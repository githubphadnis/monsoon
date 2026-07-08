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
