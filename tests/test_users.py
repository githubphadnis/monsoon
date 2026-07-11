from app.config import Settings
from app.services.sender_identity import (
    is_self_chat,
    phone_from_chat_id,
    resolve_sender_phone,
)


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


def test_resolve_sender_phone_group_participant():
    """Group messages: remoteJid is @g.us; sender phone is participant."""
    settings = Settings(
        allowed_whatsapp_numbers="918291882204,46704098198",
        monsoon_allow_self_chat=True,
    )
    phone = resolve_sender_phone(
        from_id="120363410556549299@g.us",
        from_me=False,
        body={"me": {"id": "918291882204@c.us"}},
        payload_extra={
            "participant": "46704098198@c.us",
            "_data": {
                "key": {
                    "remoteJid": "120363410556549299@g.us",
                    "participant": "46704098198@c.us",
                }
            },
        },
        settings=settings,
    )
    assert phone == "46704098198"


def test_resolve_sender_phone_group_participant_alt():
    settings = Settings(
        allowed_whatsapp_numbers="46704098198",
        monsoon_allow_self_chat=True,
    )
    phone = resolve_sender_phone(
        from_id="120363410556549299@g.us",
        from_me=False,
        body={},
        payload_extra={
            "_data": {
                "key": {
                    "remoteJid": "120363410556549299@g.us",
                    "participant": "555666777@lid",
                    "participantAlt": "46704098198@s.whatsapp.net",
                }
            },
        },
        settings=settings,
    )
    assert phone == "46704098198"


def test_resolve_sender_phone_inbound_peer_lid_via_alt():
    """1:1 inbound often arrives as @lid; phone is in remoteJidAlt."""
    settings = Settings(
        allowed_whatsapp_numbers="918291882204,919876543210",
        monsoon_allow_self_chat=True,
    )
    phone = resolve_sender_phone(
        from_id="555666777888@lid",
        from_me=False,
        body={"me": {"id": "918291882204@c.us"}},
        payload_extra={
            "_data": {"key": {"remoteJidAlt": "919876543210@s.whatsapp.net"}},
        },
        settings=settings,
    )
    assert phone == "919876543210"



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


def test_is_self_chat():
    assert is_self_chat("918291882204@c.us", "918291882204@c.us")
    assert is_self_chat("918291882204@s.whatsapp.net", "918291882204@c.us")
    assert not is_self_chat("919876543210@c.us", "918291882204@c.us")


def test_resolve_reply_chat_id_lid_to_cus():
    from app.services.sender_identity import resolve_reply_chat_id

    chat = resolve_reply_chat_id(
        "29304595423273@lid",
        {"_data": {"key": {"remoteJidAlt": "918291882204@s.whatsapp.net"}}},
    )
    assert chat == "918291882204@c.us"


def test_resolve_reply_chat_id_lid_falls_back_to_me():
    from app.services.sender_identity import resolve_reply_chat_id

    chat = resolve_reply_chat_id(
        "29304595423273@lid",
        {},
        me_id="918291882204@c.us",
    )
    assert chat == "918291882204@c.us"


def test_inbound_peer_chat_id_from_alt():
    from app.services.sender_identity import resolve_conversation_chat_id

    chat = resolve_conversation_chat_id(
        "555666777888@lid",
        {"_data": {"key": {"remoteJid": "555666777888@lid", "remoteJidAlt": "919876543210@s.whatsapp.net"}}},
        from_me=False,
        to_id="918291882204@c.us",
        me_id="918291882204@c.us",
    )
    assert chat == "919876543210@c.us"
