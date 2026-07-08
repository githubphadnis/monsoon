from app.config import Settings
from app.services.sender_identity import (
    is_chat_allowed,
    resolve_conversation_chat_id,
)


def test_chat_allowlist_denies_all_when_empty():
    assert not is_chat_allowed("918291882204@c.us", Settings())


def test_chat_allowlist_restricts_to_configured_chat():
    settings = Settings(allowed_whatsapp_chat_ids="918291882204@c.us")
    assert is_chat_allowed("918291882204@c.us", settings)
    assert is_chat_allowed("918291882204@s.whatsapp.net", settings)
    assert not is_chat_allowed("120363000000000@g.us", settings)


def test_outgoing_uses_to_field_as_chat():
    chat_id = resolve_conversation_chat_id(
        "918291882204@lid",
        {"_data": {"key": {"remoteJid": "120363000000000@g.us"}}},
        from_me=True,
        to_id="120363000000000@g.us",
        me_id="918291882204@c.us",
    )
    assert chat_id == "120363000000000@g.us"
    settings = Settings(allowed_whatsapp_chat_ids="918291882204@c.us")
    assert not is_chat_allowed(chat_id, settings)


def test_incoming_uses_from_not_to():
    # Inbound 1:1 — to is yourself; conversation is the peer.
    chat_id = resolve_conversation_chat_id(
        "919999999999@c.us",
        {},
        from_me=False,
        to_id="918291882204@c.us",
        me_id="918291882204@c.us",
    )
    assert chat_id == "919999999999@c.us"
    settings = Settings(allowed_whatsapp_chat_ids="918291882204@c.us")
    assert not is_chat_allowed(chat_id, settings)
