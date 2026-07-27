"""
Tests for the Socket.IO `join` handler's room-membership check (piece 2):
creator-of-the-room, has-a-sessions-row, and neither.

What these do NOT cover (see also conftest.py's module docstring):
  - The real Socket.IO/Engine.IO wire path. These call `main.join(sid, data)`
    directly with a made-up sid and a pre-seeded fake session, never a real
    connected client.
  - Whether the frontend's `auth` callback shape matches what `connect`
    reads - not relevant to `join` specifically, but the same caveat as
    test_connect.py applies to this whole suite: it proves the server-side
    authorization logic is correct, not that a real browser round-trip
    reaches it the way we assume.
"""
from conftest import USER_ID, FakeResponse, patch_supabase_get

from app import main

ROOM_ID = "room-1"
OTHER_USER_ID = "22222222-2222-2222-2222-222222222222"


def _rooms_response(creator, code="print('hi')"):
    def router(url):
        assert "/rest/v1/rooms" in url
        return FakeResponse([{"creator": creator, "code": code}])

    return router


async def test_join_allows_room_creator(fake_session_store, fake_room_ops, monkeypatch):
    sid = "sid-creator"
    await fake_session_store.save_session(sid, {"user_id": USER_ID})
    patch_supabase_get(monkeypatch, _rooms_response(creator=USER_ID, code="print('mine')"))

    await main.join(sid, {"room_id": ROOM_ID})

    fake_room_ops["enter_room"].assert_awaited_once_with(sid, ROOM_ID)
    fake_room_ops["emit"].assert_awaited_once_with(
        "initial-code", {"code": "print('mine')"}, to=sid
    )


async def test_join_allows_user_with_sessions_row(fake_session_store, fake_room_ops, monkeypatch):
    sid = "sid-member"
    await fake_session_store.save_session(sid, {"user_id": USER_ID})

    def router(url):
        if "/rest/v1/rooms" in url:
            return FakeResponse([{"creator": OTHER_USER_ID, "code": "print('theirs')"}])
        assert "/rest/v1/sessions" in url
        return FakeResponse([{"user_id": USER_ID}])

    patch_supabase_get(monkeypatch, router)

    await main.join(sid, {"room_id": ROOM_ID})

    fake_room_ops["enter_room"].assert_awaited_once_with(sid, ROOM_ID)
    fake_room_ops["emit"].assert_awaited_once_with(
        "initial-code", {"code": "print('theirs')"}, to=sid
    )


async def test_join_denies_user_with_neither(fake_session_store, fake_room_ops, monkeypatch):
    sid = "sid-stranger"
    await fake_session_store.save_session(sid, {"user_id": USER_ID})

    def router(url):
        if "/rest/v1/rooms" in url:
            return FakeResponse([{"creator": OTHER_USER_ID, "code": "print('theirs')"}])
        assert "/rest/v1/sessions" in url
        return FakeResponse([])  # no membership row

    patch_supabase_get(monkeypatch, router)

    await main.join(sid, {"room_id": ROOM_ID})

    fake_room_ops["enter_room"].assert_not_awaited()
    fake_room_ops["emit"].assert_awaited_once_with(
        "join-error",
        {"message": "You don't have access to this room."},
        to=sid,
    )


async def test_join_does_not_wipe_user_id_from_connect(
    fake_session_store, fake_room_ops, monkeypatch
):
    """Regression test for the bug fixed in piece 2: join() used to
    overwrite the whole session with {"room_id": ...}, erasing the user_id
    connect() had just stored. A bare mock wouldn't catch this - only a
    real read-modify-write session does."""
    sid = "sid-regression"
    await fake_session_store.save_session(sid, {"user_id": USER_ID})
    patch_supabase_get(monkeypatch, _rooms_response(creator=USER_ID))

    await main.join(sid, {"room_id": ROOM_ID})

    session = await fake_session_store.get_session(sid)
    assert session["user_id"] == USER_ID
    assert session["room_id"] == ROOM_ID
