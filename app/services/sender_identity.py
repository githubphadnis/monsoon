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


def _phone_candidates_from_payload(
    *,
    from_id: str,
    from_me: bool | None,
    body: dict[str, Any],
    payload_extra: dict[str, Any] | None,
    settings: Settings,
) -> list[str]:
    """Collect possible phone digits for allowlist matching.

    WhatsApp often delivers peers as ``@lid``. The real ``@c.us`` / ``@s.whatsapp.net``
    JID usually sits in ``participantAlt`` / ``remoteJidAlt``.

    For **groups**, ``remoteJid`` is the group (``…@g.us``) — that is NOT a sender phone.
    Prefer ``participant`` / ``participantAlt`` / ``author`` first.
    """
    candidates: list[str] = []
    extra = payload_extra or {}
    data = extra.get("_data") if isinstance(extra.get("_data"), dict) else {}
    key = data.get("key") if isinstance(data.get("key"), dict) else {}

    def _add(jid: object) -> None:
        if not isinstance(jid, str) or not jid.strip():
            return
        j = jid.strip()
        # Group / broadcast JIDs are never sender phones
        if j.endswith("@g.us") or j.endswith("@broadcast"):
            return
        if j.endswith("@lid"):
            return
        phone = phone_from_chat_id(j)
        if phone and phone not in candidates:
            # Skip obvious group-id shaped numbers mistakenly scraped
            if len(phone) > 15:
                return
            candidates.append(phone)

    # 1) Group sender fields first
    for field in ("participantAlt", "participant", "author"):
        _add(key.get(field))
        _add(extra.get(field))

    # 2) Direct from / alts (1:1 and some WAHA shapes)
    _add(from_id)
    for field in ("remoteJidAlt", "senderAlt", "senderPn"):
        _add(key.get(field))
        _add(extra.get(field))

    # remoteJid only if not a group (already filtered in _add)
    _add(key.get("remoteJid"))

    if from_me and settings.monsoon_allow_self_chat:
        me = body.get("me")
        if isinstance(me, dict) and me.get("id"):
            _add(str(me["id"]))

    return candidates


def resolve_sender_phone(
    *,
    from_id: str,
    from_me: bool | None,
    body: dict[str, Any],
    payload_extra: dict[str, Any] | None,
    settings: Settings,
) -> str | None:
    """Map WAHA sender id to an allowed phone (handles @lid via remoteJidAlt)."""
    for phone in _phone_candidates_from_payload(
        from_id=from_id,
        from_me=from_me,
        body=body,
        payload_extra=payload_extra,
        settings=settings,
    ):
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
    candidates = [
        key.get("remoteJid"),
        key.get("remoteJidAlt"),
        extra.get("from"),
        extra.get("chatId"),
    ]
    # 1) Group chats — never collapse to a member phone via remoteJidAlt
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.endswith("@g.us"):
            return candidate
    # 2) Real phone JIDs (1:1)
    for candidate in candidates:
        if not isinstance(candidate, str) or not candidate:
            continue
        if candidate.endswith("@lid") or candidate.endswith("@g.us"):
            continue
        return _to_cus_jid(candidate)
    # 3) Opaque lid last
    for candidate in candidates:
        if isinstance(candidate, str) and candidate:
            return _to_cus_jid(candidate)
    return None


def resolve_group_participant_key(
    *,
    from_id: str,
    payload_extra: dict[str, Any] | None,
) -> str | None:
    """Best-effort sender key for an allowlisted group (phone preferred, else lid digits)."""
    extra = payload_extra or {}
    data = extra.get("_data") if isinstance(extra.get("_data"), dict) else {}
    key = data.get("key") if isinstance(data.get("key"), dict) else {}

    raw_values: list[str] = []
    for field in (
        "participantAlt",
        "participant",
        "author",
        "senderPn",
        "senderAlt",
    ):
        for source in (key, extra):
            value = source.get(field)
            if isinstance(value, str) and value.strip():
                raw_values.append(value.strip())
    if isinstance(from_id, str) and from_id.strip():
        raw_values.append(from_id.strip())

    # Prefer real phone JIDs
    for j in raw_values:
        if j.endswith("@g.us") or j.endswith("@broadcast") or j.endswith("@lid"):
            continue
        phone = phone_from_chat_id(j)
        if phone and len(phone) <= 15:
            return phone

    # Fall back to opaque lid so we still create a per-sender user row
    for j in raw_values:
        if j.endswith("@lid"):
            lid = phone_from_chat_id(j)
            if lid:
                return f"lid:{lid}"
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
        if remote and not remote.endswith("@lid"):
            return remote
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


def is_self_chat(chat_id: str, me_id: str | None) -> bool:
    """True when the conversation is Message-yourself (chat == me)."""
    if not me_id:
        return False
    return bool(chat_id_aliases(chat_id) & chat_id_aliases(me_id))


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


def is_shared_chat(chat_id: str, settings: Settings) -> bool:
    """True when this conversation is a shared family/space chat (pooled context)."""
    shared = settings.shared_chat_ids_set
    if not shared:
        return False
    candidates = chat_id_aliases(chat_id)
    for entry in shared:
        if candidates & chat_id_aliases(entry):
            return True
    return False
