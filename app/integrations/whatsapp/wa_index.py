"""WAHA chat/message helpers for indexing."""

from __future__ import annotations

from datetime import UTC, datetime


def chat_type_from_id(chat_id: str) -> str:
    if chat_id.endswith("@g.us"):
        return "group"
    if chat_id.endswith("@c.us") or chat_id.endswith("@s.whatsapp.net"):
        return "direct"
    if chat_id.endswith("@lid"):
        return "lid"
    if chat_id == "status@broadcast":
        return "status"
    if chat_id.endswith("@newsletter"):
        return "channel"
    return "unknown"


def phone_from_jid(jid: str | None) -> str | None:
    if not jid:
        return None
    if not (jid.endswith("@c.us") or jid.endswith("@s.whatsapp.net")):
        return None
    local = jid.split("@", 1)[0]
    digits = "".join(c for c in local if c.isdigit())
    if len(digits) < 8:
        return None
    return digits


def timestamp_to_datetime(ts: int | float | None) -> datetime | None:
    if ts is None:
        return None
    try:
        value = float(ts)
    except (TypeError, ValueError):
        return None
    if value > 1_000_000_000_000:
        value /= 1000.0
    return datetime.fromtimestamp(value, tz=UTC)


def message_fields(raw: dict) -> dict:
    """Normalise WAHA message dict to index fields."""
    msg_id = str(raw.get("id") or raw.get("_id") or "")
    ts = raw.get("timestamp") or raw.get("t")
    body = raw.get("body") or raw.get("text") or raw.get("caption")
    return {
        "waha_message_id": msg_id,
        "from_id": raw.get("from") or raw.get("author"),
        "from_me": raw.get("fromMe") if "fromMe" in raw else raw.get("from_me"),
        "body": body,
        "has_media": bool(raw.get("hasMedia") or raw.get("has_media")),
        "message_ts_raw": int(ts) if ts is not None else None,
        "message_ts": timestamp_to_datetime(ts if isinstance(ts, (int, float)) else None),
    }


def chat_fields(raw: dict) -> dict:
    chat_id = str(raw.get("id") or raw.get("chatId") or "")
    name = raw.get("name") or raw.get("pushName") or raw.get("subject")
    ts = raw.get("timestamp") or raw.get("conversationTimestamp") or raw.get("t")
    return {
        "chat_id": chat_id,
        "name": name,
        "chat_type": chat_type_from_id(chat_id),
        "last_message_at": timestamp_to_datetime(ts if isinstance(ts, (int, float)) else None),
    }
