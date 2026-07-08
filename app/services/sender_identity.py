"""WhatsApp sender id → allowed phone resolution (no DB)."""

from typing import Any

from app.config import Settings


def phone_from_chat_id(chat_id: str) -> str:
    """Extract phone digits from WAHA chat id (c.us, s.whatsapp.net, lid, …)."""
    return chat_id.split("@", 1)[0]


def is_allowed_sender(phone: str, settings: Settings) -> bool:
    allowed = settings.allowed_numbers_set
    if not allowed:
        return True
    return phone in allowed


def resolve_sender_phone(
    *,
    from_id: str,
    from_me: bool | None,
    body: dict[str, Any],
    payload_extra: dict[str, Any] | None,
    settings: Settings,
) -> str | None:
    """Map WAHA sender id to an allowed phone (self-chat uses @lid, not @c.us)."""
    candidates: list[str] = [phone_from_chat_id(from_id)]

    if from_me and settings.monsoon_allow_self_chat:
        me = body.get("me")
        if isinstance(me, dict) and me.get("id"):
            candidates.append(phone_from_chat_id(str(me["id"])))

        extra = payload_extra or {}
        data = extra.get("_data") if isinstance(extra.get("_data"), dict) else {}
        key = data.get("key") if isinstance(data.get("key"), dict) else {}
        alt = key.get("remoteJidAlt")
        if alt:
            candidates.append(phone_from_chat_id(str(alt)))

    for phone in candidates:
        if is_allowed_sender(phone, settings):
            return phone
    return None


def _to_cus_jid(jid: str) -> str:
    if jid.endswith("@c.us"):
        return jid
    if jid.endswith("@s.whatsapp.net"):
        return f"{phone_from_chat_id(jid)}@c.us"
    return jid


def _extract_remote_jid(payload_extra: dict[str, Any] | None) -> str | None:
    extra = payload_extra or {}
    data = extra.get("_data") if isinstance(extra.get("_data"), dict) else {}
    key = data.get("key") if isinstance(data.get("key"), dict) else {}
    for candidate in (key.get("remoteJidAlt"), key.get("remoteJid")):
        if isinstance(candidate, str) and candidate:
            return _to_cus_jid(candidate)
    return None


def resolve_reply_chat_id(
    from_id: str,
    payload_extra: dict[str, Any] | None,
    *,
    to_id: str | None = None,
    me_id: str | None = None,
) -> str:
    """Resolve the actual conversation JID for replies / allowlist checks."""
    if to_id:
        return _to_cus_jid(to_id)

    remote = _extract_remote_jid(payload_extra)
    if remote:
        return remote

    if not from_id.endswith("@lid"):
        return _to_cus_jid(from_id)

    if me_id:
        return _to_cus_jid(me_id)

    return _to_cus_jid(from_id)
