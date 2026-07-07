from datetime import UTC

from app.integrations.whatsapp.wa_index import (
    chat_fields,
    chat_type_from_id,
    message_fields,
    phone_from_jid,
    timestamp_to_datetime,
)
from app.services.wa_entity_extract import extract_entities_from_text


def test_chat_type_from_id():
    assert chat_type_from_id("918291882204@c.us") == "direct"
    assert chat_type_from_id("123@g.us") == "group"


def test_phone_from_jid():
    assert phone_from_jid("918291882204@c.us") == "918291882204"
    assert phone_from_jid("29304595423273@lid") is None


def test_timestamp_to_datetime_seconds():
    dt = timestamp_to_datetime(1_700_000_000)
    assert dt is not None
    assert dt.tzinfo == UTC


def test_message_fields():
    raw = {
        "id": "msg_1",
        "timestamp": 1_700_000_000,
        "from": "918291882204@c.us",
        "fromMe": True,
        "body": "todo test",
        "hasMedia": False,
    }
    fields = message_fields(raw)
    assert fields["waha_message_id"] == "msg_1"
    assert fields["body"] == "todo test"
    assert fields["from_me"] is True


def test_chat_fields():
    raw = {"id": "918291882204@c.us", "name": "Self", "timestamp": 1_700_000_000}
    fields = chat_fields(raw)
    assert fields["chat_id"] == "918291882204@c.us"
    assert fields["name"] == "Self"
    assert fields["chat_type"] == "direct"


def test_extract_entities_from_text():
    text = "Call +31 6 12345678 or email prakalp@example.com https://example.com"
    types = {t for t, _ in extract_entities_from_text(text)}
    assert "email" in types
    assert "url" in types
    assert "phone" in types
