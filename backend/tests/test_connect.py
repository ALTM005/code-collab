"""
Tests for the Socket.IO `connect` handler's token verification (piece 1: the
handshake auth gate; piece 3: audience/issuer enforcement in verify_token).

What these do NOT cover (see also conftest.py's module docstring):
  - The real Socket.IO/Engine.IO wire path. These call `main.connect(sid,
    environ, auth)` directly with a made-up sid and a hand-built `auth`
    dict - a real client's `auth` payload arrives through the Engine.IO
    handshake, which this suite never touches.
  - Whether the frontend's `auth: (cb) => cb({ token: ... })` callback in
    Room.tsx actually produces `{"token": "..."}` by the time python-socketio
    hands it to this function. That's a client/server contract this suite
    can't see from the backend side alone - only a real connection (or the
    manual test after piece 3) verifies that end to end.
"""
import asyncio
import time

import pytest

from app import main
from conftest import USER_ID, make_token

ENVIRON: dict = {}


@pytest.mark.parametrize(
    "auth_payload",
    [None, {}, {"token": ""}],
    ids=["auth-none", "auth-empty-dict", "auth-empty-token"],
)
async def test_connect_refuses_missing_token_cleanly(auth_payload):
    # Each of these must refuse via ConnectionRefusedError, not blow up with
    # a TypeError from `(auth or {}).get(...)` on some unexpected shape.
    with pytest.raises(main.ConnectionRefusedError):
        await main.connect("sid-missing", ENVIRON, auth_payload)


async def test_connect_refuses_malformed_token():
    with pytest.raises(main.ConnectionRefusedError):
        await main.connect("sid-malformed", ENVIRON, {"token": "not-a-jwt"})


async def test_connect_refuses_expired_token():
    token = make_token(exp=int(time.time()) - 3600)
    with pytest.raises(main.ConnectionRefusedError):
        await main.connect("sid-expired", ENVIRON, {"token": token})


async def test_connect_refuses_wrong_issuer():
    token = make_token(iss="https://not-your-project.supabase.co/auth/v1")
    with pytest.raises(main.ConnectionRefusedError):
        await main.connect("sid-wrong-iss", ENVIRON, {"token": token})


async def test_connect_refuses_missing_aud():
    token = make_token(omit=("aud",))
    with pytest.raises(main.ConnectionRefusedError):
        await main.connect("sid-no-aud", ENVIRON, {"token": token})


async def test_connect_accepts_valid_token(fake_session_store):
    token = make_token()

    await main.connect("sid-valid", ENVIRON, {"token": token})

    session = await main.sio.get_session("sid-valid")
    assert session["user_id"] == USER_ID

    # connect() also schedules a task to disconnect this socket at the
    # token's expiry - confirm it was scheduled, then clean it up so it
    # doesn't outlive the test.
    task = main.socket_expiry_tasks.pop("sid-valid", None)
    assert task is not None
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
