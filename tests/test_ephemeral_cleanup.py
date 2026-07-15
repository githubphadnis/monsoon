"""Tests for ephemeral WhatsApp cleanup."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.config import Settings
from app.models import InboundMessage, OutboundMessage
from app.services.ephemeral_cleanup import (
    EphemeralCleanupService,
    extract_waha_message_id,
    serialize_waha_message_id,
)


def test_extract_waha_message_id_string():
    assert extract_waha_message_id({"id": "true_1@c.us_AAA"}) == "true_1@c.us_AAA"


def test_extract_waha_message_id_nested():
    assert (
        extract_waha_message_id({"id": {"_serialized": "true_1@c.us_BBB"}})
        == "true_1@c.us_BBB"
    )


def test_serialize_bare_hash_for_delete():
    assert (
        serialize_waha_message_id(
            "120363427281353392@g.us", "3EB03BF95638667DBCDE3A", from_me=True
        )
        == "true_120363427281353392@g.us_3EB03BF95638667DBCDE3A"
    )
    assert (
        serialize_waha_message_id(
            "918291884406@c.us", "false_918291884406@c.us_CMD", from_me=False
        )
        == "false_918291884406@c.us_CMD"
    )


@pytest.mark.asyncio
async def test_ephemeral_serializes_bare_outbound_id():
    settings = Settings(monsoon_ephemeral_seconds=60, monsoon_ephemeral_delete_commands=False)
    db = MagicMock()
    old = OutboundMessage(
        channel="whatsapp",
        recipient="120363427281353392@g.us",
        message_body="Saved · milk",
        status="sent",
        provider_message_id="3EB03BF95638667DBCDE3A",
        sent_at=datetime.now(UTC) - timedelta(minutes=5),
        waha_session="prakalp",
    )
    db.scalars.return_value = [old]
    waha = MagicMock()
    waha.delete_message = AsyncMock()

    stats = await EphemeralCleanupService(db, settings, waha=waha).run()

    waha.delete_message.assert_awaited_once_with(
        "120363427281353392@g.us",
        "true_120363427281353392@g.us_3EB03BF95638667DBCDE3A",
        session="prakalp",
    )
    assert old.status == "deleted"
    assert stats.outbound_deleted == 1


@pytest.mark.asyncio
async def test_ephemeral_deletes_old_outbound():
    settings = Settings(monsoon_ephemeral_seconds=60, monsoon_ephemeral_delete_commands=False)
    db = MagicMock()
    old = OutboundMessage(
        channel="whatsapp",
        recipient="918291884406@c.us",
        message_body="hello",
        status="sent",
        provider_message_id="true_918291884406@c.us_XYZ",
        sent_at=datetime.now(UTC) - timedelta(minutes=5),
    )
    db.scalars.return_value = [old]
    waha = MagicMock()
    waha.delete_message = AsyncMock()

    stats = await EphemeralCleanupService(db, settings, waha=waha).run()

    waha.delete_message.assert_awaited_once_with(
        "918291884406@c.us",
        "true_918291884406@c.us_XYZ",
        session="default",
    )
    assert old.status == "deleted"
    assert stats.outbound_deleted == 1
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_ephemeral_disabled():
    settings = Settings(monsoon_ephemeral_seconds=0)
    db = MagicMock()
    waha = MagicMock()
    waha.delete_message = AsyncMock()

    stats = await EphemeralCleanupService(db, settings, waha=waha).run()

    waha.delete_message.assert_not_awaited()
    assert stats.outbound_deleted == 0


@pytest.mark.asyncio
async def test_ephemeral_deletes_inbound_commands():
    settings = Settings(monsoon_ephemeral_seconds=60, monsoon_ephemeral_delete_commands=True)
    db = MagicMock()
    outbound_empty = []
    inbound = InboundMessage(
        source="whatsapp",
        source_message_id="false_918291884406@c.us_CMD",
        sender_id="918291884406@c.us",
        chat_id="918291884406@c.us",
        status="processed",
        received_at=datetime.now(UTC) - timedelta(minutes=10),
    )

    def _scalars(stmt):  # noqa: ARG001
        # First call outbound, second inbound — EphemeralCleanupService order
        if not hasattr(_scalars, "n"):
            _scalars.n = 0
        _scalars.n += 1
        return outbound_empty if _scalars.n == 1 else [inbound]

    db.scalars.side_effect = _scalars
    waha = MagicMock()
    waha.delete_message = AsyncMock()

    stats = await EphemeralCleanupService(db, settings, waha=waha).run()

    waha.delete_message.assert_awaited_once_with(
        "918291884406@c.us", "false_918291884406@c.us_CMD", session="default"
    )
    assert inbound.status == "deleted"
    assert stats.inbound_deleted == 1
