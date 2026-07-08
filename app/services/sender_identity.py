"""WhatsApp sender / chat JID resolution (no DB)."""

from __future__ import annotations

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


def normalize_chat_id(jid: str) -> str:
    """Canonical form for allowlist comparison (@s.whatsapp.net → @c.us)."""
    return _to_cus_jid(jid.strip())


def chat_id_aliases(jid: str) -> set[str]:
    """Forms that may appear in WAHA payloads for the same conversation."""
    n = normalize_chat_id(jid)
    aliases = {jid.strip(), n}
    if n.endswith("@c.us"):
        phone = phone_from_chat_id(n)
        aliases.add(f"{phone}@s.whatsapp.net")
        aliases.add(phone)
    return {a for a in aliases if a}


def _extract_remote_jid(payload_extra: dict[str, Any] | None) -> str | None:
    extra = payload_extra or {}
    data = extra.get("_data") if isinstance(extra.get("_data"), dict) else {}
    key = data.get("key") if isinstance(data.get("key"), dict) else {}
    for candidate in (key.get("remoteJidAlt"), key.get("remoteJid")):
        if isinstance(candidate, str) and candidate:
            return _to_cus_jid(candidate)
    return None


def resolve_conversation_chat_id(
    from_id: str,
    payload_extra: dict[str, Any] | None,
    *,
    from_me: bool | None = None,
    to_id: str | None = None,
    me_id: str | None = None,
) -> str:
    """Resolve the conversation JID to reply into / allowlist against.

    - Incoming (fromMe=false): conversation is the remote peer / group (`from` / remoteJid).
    - Outgoing (fromMe=true): conversation is the recipient (`to` / remoteJid), not "me".
    """
    if from_me:
        if to_id:
            return _to_cus_jid(to_id)
        remote = _extract_remote_jid(payload_extra)
        if remote:
            return remote
        if me_id:
            return _to_cus_jid(me_id)
        return _to_cus_jid(from_id)

    remote = _extract_remote_jid(payload_extra)
    if remote and not remote.endswith("@lid"):
        return remote
    if from_id and not from_id.endswith("@lid"):
        return _to_cus_jid(from_id)
    if remote:
        return remote
    if me_id:
        return _to_cus_jid(me_id)
    return _to_cus_jid(from_id)


# Back-compat alias used by older call sites / tests
def resolve_reply_chat_id(
    from_id: str,
    payload_extra: dict[str, Any] | None,
    *,
    to_id: str | None = None,
    me_id: str | None = None,
    from_me: bool | None = None,
) -> str:
    return resolve_conversation_chat_id(
        from_id,
        payload_extra,
        from_me=from_me,
        to_id=to_id,
        me_id=me_id,
    )


def is_chat_allowed(chat_id: str, settings: Settings) -> bool:
    """Strict chat allowlist: only listed conversation JIDs may receive monsoon replies.

    Empty allowlist → deny all (fail closed). Set ALLOWED_WHATSAPP_CHAT_IDS explicitly.
    """
    allowed = settings.allowed_chat_ids_set
    if not allowed:
        return False
    candidates = chat_id_aliases(chat_id)
    for entry in allowed:
        if candidates & chat_id_aliases(entry):
            return True
    return False
