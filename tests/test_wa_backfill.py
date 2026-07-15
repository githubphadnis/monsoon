"""Tests for WA backfill contact deduplication."""

import asyncio
from unittest.mock import MagicMock

import pytest

from app.config import Settings
from app.services.wa_backfill import BackfillStats, ProgressEvent, WaBackfillService


def test_upsert_contact_dedupes_pending_same_jid():
    """status@broadcast chat + messages must not INSERT duplicate contacts before flush."""
    db = MagicMock()
    db.scalar.return_value = None
    service = WaBackfillService(db, Settings(waha_session="prakalp"))
    stats = BackfillStats()

    service._upsert_contact(
        jid="status@broadcast",
        display_name="Status",
        contact_type="status",
        raw={"id": "status@broadcast"},
        stats=stats,
    )
    service._upsert_contact(
        jid="status@broadcast",
        display_name=None,
        contact_type="participant",
        raw={"from": "status@broadcast"},
        stats=stats,
    )
    service._upsert_contact(
        jid="status@broadcast",
        display_name=None,
        contact_type="participant",
        raw={"from": "status@broadcast"},
        stats=stats,
    )

    assert stats.contacts_upserted == 1
    assert db.add.call_count == 1


def test_index_message_skips_contact_when_from_id_is_chat_id():
    db = MagicMock()
    db.scalar.return_value = None
    service = WaBackfillService(db, Settings(waha_session="prakalp"))
    stats = BackfillStats()
    chat = MagicMock()
    chat.id = "chat-uuid"
    chat.chat_id = "status@broadcast"

    service._index_message(
        chat,
        {
            "id": "msg-1",
            "from": "status@broadcast",
            "body": "hello",
            "timestamp": 1,
        },
        stats,
    )

    db.add.assert_called()  # WaMessage added
    for call in db.add.call_args_list:
        args = call[0]
        if args and hasattr(args[0], "jid"):
            pytest.fail("should not add WaContact when from_id equals chat_id")


@pytest.mark.asyncio
async def test_progress_callback_receives_start_event():
    events: list[ProgressEvent] = []
    db = MagicMock()
    db.scalars.return_value = []
    db.get.return_value = None

    async def _boom(*_a, **_k):
        raise ConnectionError("offline")

    service = WaBackfillService(
        db,
        Settings(waha_session="prakalp"),
        on_progress=events.append,
    )
    service._waha.list_chats = _boom  # type: ignore[method-assign]

    stats = await service.run(full=True, max_chats=1)
    assert events and events[0].phase == "start"
    assert events[0].session == "prakalp"
    assert stats.errors
