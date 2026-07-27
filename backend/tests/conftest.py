"""
Shared fakes for the connect/join test suite.

Scope note (applies to every test file in this directory): these tests call
app.main's `connect` and `join` coroutines directly with a fabricated `sid`.
They do NOT drive the real Socket.IO/Engine.IO wire protocol - a real client
goes through a handshake that assigns and registers that `sid` before any
event handler runs, and python-socketio's session storage (`get_session`/
`save_session`) requires that registration to exist. That transport layer is
python-socketio's own code, not ours, so it isn't exercised here - these
tests are strictly about our authorization logic (verify_token, the
creator/sessions membership check), not the wire path that reaches it.
"""
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest
from jose import jwt as jose_jwt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import main  # noqa: E402

USER_ID = "11111111-1111-1111-1111-111111111111"


class FakeSessionStore:
    """Mimics sio.get_session/save_session/session() with a real dict per
    sid, so state actually round-trips across calls within a test. A bare
    AsyncMock would accept any save_session call, including one that
    clobbers the session, without ever catching that regression."""

    def __init__(self):
        self.sessions: dict[str, dict] = {}

    async def get_session(self, sid, namespace=None):
        return self.sessions.setdefault(sid, {})

    async def save_session(self, sid, session, namespace=None):
        self.sessions[sid] = session

    def session(self, sid, namespace=None):
        store = self

        class _Ctx:
            async def __aenter__(ctx_self):
                ctx_self.value = await store.get_session(sid)
                return ctx_self.value

            async def __aexit__(ctx_self, *exc):
                await store.save_session(sid, ctx_self.value)

        return _Ctx()


@pytest.fixture
def fake_session_store(monkeypatch):
    store = FakeSessionStore()
    monkeypatch.setattr(main.sio, "get_session", store.get_session)
    monkeypatch.setattr(main.sio, "save_session", store.save_session)
    monkeypatch.setattr(main.sio, "session", store.session)
    return store


@pytest.fixture
def fake_room_ops(monkeypatch):
    """Patch the side-effecting sio calls join()/connect() make, so a test
    can assert on them without a real connected client behind `sid`."""
    ops = {
        "enter_room": AsyncMock(),
        "emit": AsyncMock(),
        "disconnect": AsyncMock(),
    }
    monkeypatch.setattr(main.sio, "enter_room", ops["enter_room"])
    monkeypatch.setattr(main.sio, "emit", ops["emit"])
    monkeypatch.setattr(main.sio, "disconnect", ops["disconnect"])
    return ops


class FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://example.test")
            raise httpx.HTTPStatusError(
                "error",
                request=request,
                response=httpx.Response(self.status_code, request=request),
            )

    def json(self):
        return self._json_data


def patch_supabase_get(monkeypatch, router):
    """router(url: str) -> FakeResponse. Replaces httpx.AsyncClient.get for
    the duration of the test so join()'s Supabase lookups never leave this
    process, let alone hit the real dev project."""

    async def fake_get(self, url, **kwargs):
        return router(url)

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)


def make_token(secret=None, omit=(), **overrides):
    claims = {
        "sub": USER_ID,
        "iss": f"{main.SUPABASE_URL}/auth/v1",
        "aud": "authenticated",
        "exp": int(time.time()) + 3600,
    }
    claims.update(overrides)
    for key in omit:
        claims.pop(key, None)
    return jose_jwt.encode(claims, secret or main.SUPABASE_JWT_SECRET, algorithm="HS256")
