"""Parse Gmail API message payloads."""

from __future__ import annotations

import base64
from datetime import UTC, datetime
from email.utils import parseaddr, parsedate_to_datetime


def header_map(payload: dict) -> dict[str, str]:
    headers = payload.get("headers") or []
    if isinstance(headers, list):
        return {h.get("name", "").lower(): h.get("value", "") for h in headers if h.get("name")}
    return {}


def parse_address_list(value: str | None) -> list[dict[str, str]]:
    if not value:
        return []
    parts = [p.strip() for p in value.split(",") if p.strip()]
    result: list[dict[str, str]] = []
    for part in parts:
        name, email = parseaddr(part)
        if email:
            result.append({"email": email.lower(), "name": name or None})
    return result


def parse_from(headers: dict[str, str]) -> tuple[str | None, str | None]:
    name, email = parseaddr(headers.get("from", ""))
    return (email.lower() if email else None, name or None)


def parse_date(headers: dict[str, str]) -> datetime | None:
    raw = headers.get("date")
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw)
    except (TypeError, ValueError, IndexError):
        return None
    # Gmail Date headers may be offset-naive; always store/compare as UTC-aware.
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def decode_body(payload: dict) -> str | None:
    """Best-effort plain text from Gmail message payload."""
    if payload.get("body", {}).get("data"):
        return _decode_b64(payload["body"]["data"])

    for part in payload.get("parts") or []:
        mime = (part.get("mimeType") or "").lower()
        if mime == "text/plain" and part.get("body", {}).get("data"):
            return _decode_b64(part["body"]["data"])
    for part in payload.get("parts") or []:
        if part.get("body", {}).get("data"):
            text = _decode_b64(part["body"]["data"])
            if text:
                return text
    return None


def _decode_b64(data: str) -> str | None:
    try:
        padded = data + "=" * (-len(data) % 4)
        return base64.urlsafe_b64decode(padded.encode()).decode("utf-8", errors="replace")
    except Exception:
        return None
