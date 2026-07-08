from app.config import Settings
from app.api.webhooks import _chat_allowed


def test_chat_allowlist_allows_all_when_empty():
    assert _chat_allowed("918291882204@c.us", Settings())


def test_chat_allowlist_restricts_to_configured_chat():
    settings = Settings(allowed_whatsapp_chat_ids="918291882204@c.us")
    assert _chat_allowed("918291882204@c.us", settings)
    assert not _chat_allowed("120363000000000@g.us", settings)
