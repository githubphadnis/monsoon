from app.config import Settings
from app.api.webhooks import _chat_allowed
from app.services.sender_identity import resolve_reply_chat_id


def test_chat_allowlist_allows_all_when_empty():
    assert _chat_allowed("918291882204@c.us", Settings())


def test_chat_allowlist_restricts_to_configured_chat():
    settings = Settings(allowed_whatsapp_chat_ids="918291882204@c.us")
    assert _chat_allowed("918291882204@c.us", settings)
    assert not _chat_allowed("120363000000000@g.us", settings)


def test_resolve_reply_chat_id_prefers_to_field_for_own_messages():
    chat_id = resolve_reply_chat_id(
        "918291882204@lid",
        {"_data": {"key": {"remoteJidAlt": "918291882204@s.whatsapp.net"}}},
        to_id="120363000000000@g.us",
        me_id="918291882204@c.us",
    )
    assert chat_id == "120363000000000@g.us"
