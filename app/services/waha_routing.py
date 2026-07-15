"""Resolve which WAHA session (and base URL) to use for a chat / phone."""

from __future__ import annotations

from app.config import Settings


def parse_colon_map(raw: str) -> dict[str, str]:
    """Parse `key:value,key2:value2` into a dict (keys lowercased for aliases, phones as digits)."""
    out: dict[str, str] = {}
    for part in (raw or "").split(","):
        part = part.strip()
        if not part or ":" not in part:
            continue
        key, value = part.split(":", 1)
        k = key.strip()
        v = value.strip()
        if k and v:
            out[k] = v
    return out


def phone_session_map(settings: Settings) -> dict[str, str]:
    """phone digits → WAHA session name."""
    raw = parse_colon_map(settings.monsoon_waha_session_map)
    return {k.lstrip("+"): v for k, v in raw.items()}


def session_endpoint_map(settings: Settings) -> dict[str, str]:
    """session name → base URL (optional; empty = use WAHA_BASE_URL)."""
    return parse_colon_map(settings.monsoon_waha_endpoints)


def all_waha_sessions(settings: Settings) -> list[str]:
    sessions = {settings.waha_session.strip()} if settings.waha_session.strip() else set()
    sessions.update(phone_session_map(settings).values())
    sessions.update(session_endpoint_map(settings).keys())
    return sorted(s for s in sessions if s)


def base_url_for_session(settings: Settings, session: str | None) -> str:
    name = (session or settings.waha_session).strip() or settings.waha_session
    endpoints = session_endpoint_map(settings)
    if name in endpoints:
        return endpoints[name].rstrip("/")
    return settings.waha_base_url.rstrip("/")


def session_for_phone(settings: Settings, phone: str | None) -> str:
    digits = (phone or "").lstrip("+").strip()
    mapped = phone_session_map(settings).get(digits)
    if mapped:
        return mapped
    return settings.waha_session


def session_for_chat_id(settings: Settings, chat_id: str) -> str:
    """Best-effort session for a conversation (1:1 → phone map; groups → primary)."""
    cid = (chat_id or "").strip()
    if cid.endswith("@g.us"):
        # Shared / group traffic is owned by the primary monsoon session.
        return settings.waha_session
    phone = cid.split("@", 1)[0].lstrip("+")
    return session_for_phone(settings, phone)


def webhook_session_owns_chat(
    settings: Settings,
    *,
    session: str | None,
    chat_id: str,
) -> bool:
    """True when this WAHA session should process the webhook for chat_id.

    Multi-session households get the *same* group message on every member
    session. Only the authoritative session (primary for groups; mapped phone
    for 1:1) should capture — otherwise we double-reply and race on different
    provider message ids.
    """
    name = (session or "").strip()
    if not name:
        return True
    expected = session_for_chat_id(settings, chat_id)
    return name == expected.strip()


def resolve_reply_session(
    settings: Settings,
    *,
    inbound_session: str | None,
    chat_id: str,
    sender_phone: str | None = None,
) -> str:
    """Pick the WAHA session that should send the reply.

    Groups always use the primary session. 1:1 prefers the phone map
    (Message yourself), then the inbound webhook session as a last resort.
    """
    cid = (chat_id or "").strip()
    if cid.endswith("@g.us"):
        return settings.waha_session
    if sender_phone:
        return session_for_phone(settings, sender_phone)
    if inbound_session and inbound_session.strip():
        return inbound_session.strip()
    return session_for_chat_id(settings, chat_id)
