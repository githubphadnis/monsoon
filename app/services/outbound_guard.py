"""Detect WhatsApp webhooks that echo monsoon's own outbound replies."""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import OutboundMessage

# Self-chat echoes bot replies with fromMe=true — match our confirmation templates.
_BOT_REPLY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^(?:Task|Note) #\d+ created:", re.IGNORECASE),
    re.compile(r"^Done — #\d+:", re.IGNORECASE),
    re.compile(r"^No task #\d+ found\.", re.IGNORECASE),
    re.compile(r"^Task #\d+ is already done\.", re.IGNORECASE),
    re.compile(r"^No tasks for ", re.IGNORECASE),
    re.compile(r"^\*today\*", re.IGNORECASE),
    re.compile(r"^\*Digest\*", re.IGNORECASE),
    re.compile(r"^Nothing open right now\.", re.IGNORECASE),
    re.compile(r"^I didn't catch that\.", re.IGNORECASE),
    re.compile(r"^Something went wrong saving that\.", re.IGNORECASE),
    re.compile(r"^monsoon — capture & remind", re.IGNORECASE),
    re.compile(r"^Usage: `done <id>`", re.IGNORECASE),
)


def is_bot_reply_text(text: str) -> bool:
    """True when body matches a monsoon outbound confirmation template."""
    normalized = text.strip()
    if not normalized:
        return False
    return any(pattern.search(normalized) for pattern in _BOT_REPLY_PATTERNS)


def is_outbound_echo(db: Session, *, message_id: str, text: str) -> bool:
    """True when this webhook is an echo of a message monsoon sent."""
    if message_id:
        known = db.scalar(
            select(OutboundMessage.id)
            .where(OutboundMessage.provider_message_id == message_id)
            .limit(1)
        )
        if known:
            return True

    normalized = text.strip()
    if normalized:
        body_match = db.scalar(
            select(OutboundMessage.id)
            .where(
                OutboundMessage.message_body == normalized,
                OutboundMessage.status == "sent",
            )
            .limit(1)
        )
        if body_match:
            return True

    return is_bot_reply_text(normalized)
