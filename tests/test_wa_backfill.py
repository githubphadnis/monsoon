"""Tests for WA backfill contact deduplication."""

from unittest.mock import MagicMock

from app.config import Settings
from app.services.wa_backfill import BackfillStats, WaBackfillService


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
