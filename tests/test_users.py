from app.config import Settings
from app.services.sender_identity import phone_from_chat_id, resolve_sender_phone


def test_phone_from_chat_id():
    assert phone_from_chat_id("918291882204@c.us") == "918291882204"
    assert phone_from_chat_id("918291882204@s.whatsapp.net") == "918291882204"


def test_resolve_sender_phone_self_chat_lid():
    settings = Settings(
        allowed_whatsapp_numbers="918291882204",
        monsoon_allow_self_chat=True,
    )
    body = {"me": {"id": "918291882204@c.us"}}
    phone = resolve_sender_phone(
        from_id="29304595423273@lid",
        from_me=True,
        body=body,
        payload_extra={},
        settings=settings,
    )
    assert phone == "918291882204"


def test_resolve_sender_phone_rejects_unknown():
    settings = Settings(allowed_whatsapp_numbers="918291882204", monsoon_allow_self_chat=True)
    phone = resolve_sender_phone(
        from_id="919004086959@s.whatsapp.net",
        from_me=False,
        body={},
        payload_extra={},
        settings=settings,
    )
    assert phone is None


def test_resolve_reply_chat_id_lid_to_cus():
    from app.services.sender_identity import resolve_reply_chat_id

    chat = resolve_reply_chat_id(
        "29304595423273@lid",
        {"_data": {"key": {"remoteJidAlt": "918291882204@s.whatsapp.net"}}},
    )
    assert chat == "918291882204@c.us"
