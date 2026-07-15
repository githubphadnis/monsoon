"""Tests for multi-session WAHA routing."""

from app.config import Settings
from app.services.waha_routing import (
    all_waha_sessions,
    base_url_for_session,
    resolve_reply_session,
    session_for_chat_id,
    session_for_phone,
    webhook_session_owns_chat,
)


def test_session_for_phone_uses_map():
    s = Settings(
        waha_session="prakalp",
        monsoon_waha_session_map="918291882204:prakalp,918291882206:rashmi",
    )
    assert session_for_phone(s, "918291882206") == "rashmi"
    assert session_for_phone(s, "999") == "prakalp"


def test_group_chat_uses_primary_session():
    s = Settings(
        waha_session="prakalp",
        monsoon_waha_session_map="918291882206:rashmi",
    )
    assert session_for_chat_id(s, "120363143633935585@g.us") == "prakalp"


def test_webhook_session_owns_group_primary_only():
    s = Settings(
        waha_session="prakalp",
        monsoon_waha_session_map="918291882206:Rashmi,46704098198:Prathamesh",
    )
    gid = "120363426840058222@g.us"
    assert webhook_session_owns_chat(s, session="prakalp", chat_id=gid)
    assert not webhook_session_owns_chat(s, session="Rashmi", chat_id=gid)
    assert not webhook_session_owns_chat(s, session="Prathamesh", chat_id=gid)


def test_resolve_reply_maps_phone_for_dm():
    s = Settings(
        waha_session="prakalp",
        monsoon_waha_session_map="918291882206:rashmi",
    )
    assert (
        resolve_reply_session(
            s,
            inbound_session="prakalp",
            chat_id="918291882206@c.us",
            sender_phone="918291882206",
        )
        == "rashmi"
    )


def test_resolve_reply_group_always_primary():
    s = Settings(
        waha_session="prakalp",
        monsoon_waha_session_map="918291882206:rashmi",
    )
    assert (
        resolve_reply_session(
            s,
            inbound_session="rashmi",
            chat_id="120363143633935585@g.us",
            sender_phone="918291882206",
        )
        == "prakalp"
    )


def test_all_sessions_and_endpoints():
    s = Settings(
        waha_session="prakalp",
        waha_base_url="http://waha:3000",
        monsoon_waha_session_map="918291882206:rashmi",
        monsoon_waha_endpoints="rashmi:http://127.0.0.1:3001",
    )
    assert set(all_waha_sessions(s)) == {"prakalp", "rashmi"}
    assert base_url_for_session(s, "prakalp") == "http://waha:3000"
    assert base_url_for_session(s, "rashmi") == "http://127.0.0.1:3001"
