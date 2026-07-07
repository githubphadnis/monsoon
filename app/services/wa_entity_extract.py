"""Regex extraction of phones, emails, URLs from message text."""

from __future__ import annotations

import re

PHONE_RE = re.compile(r"(?:\+?\d[\d\s\-().]{7,}\d)")
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
URL_RE = re.compile(r"https?://[^\s<>\"']+")


def _normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw)
    return digits.lstrip("0") if digits else ""


def extract_entities_from_text(text: str) -> list[tuple[str, str]]:
    """Return list of (entity_type, value)."""
    if not text or not text.strip():
        return []

    found: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for match in EMAIL_RE.finditer(text):
        value = match.group(0).lower()
        key = ("email", value)
        if key not in seen:
            seen.add(key)
            found.append(key)

    for match in URL_RE.finditer(text):
        value = match.group(0).rstrip(".,);]")
        key = ("url", value)
        if key not in seen:
            seen.add(key)
            found.append(key)

    for match in PHONE_RE.finditer(text):
        value = _normalize_phone(match.group(0))
        if len(value) < 8:
            continue
        key = ("phone", value)
        if key not in seen:
            seen.add(key)
            found.append(key)

    return found
