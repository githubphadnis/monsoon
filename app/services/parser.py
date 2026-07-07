"""Command parsing — regex first, Ollama fallback."""

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.config import Settings
from app.integrations.ollama.client import OllamaClient
from app.schemas.capture import ParsedCapture

TODO_RE = re.compile(r"^to[\s-]*do\s+(.+)$", re.IGNORECASE)
NOTE_RE = re.compile(r"^note\s+(.+)$", re.IGNORECASE)
DONE_RE = re.compile(r"^done\s+(\d+)$", re.IGNORECASE)
LIST_RE = re.compile(r"^list(?:\s+(\w+))?$", re.IGNORECASE)
DIGEST_RE = re.compile(r"^digest(?:\s+now)?$", re.IGNORECASE)
HELP_RE = re.compile(r"^help$", re.IGNORECASE)

RELATIVE_RE = re.compile(
    r"\b(tomorrow|today)\b(?:\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?)?",
    re.IGNORECASE,
)


def _local_now(settings: Settings) -> datetime:
    return datetime.now(ZoneInfo(settings.app_timezone))


def _apply_relative_datetime(text: str, settings: Settings) -> tuple[str, datetime | None]:
    match = RELATIVE_RE.search(text)
    if not match:
        return text, None

    when = match.group(1).lower()
    hour = int(match.group(2) or 9)
    minute = int(match.group(3) or 0)
    ampm = (match.group(4) or "").lower()
    if ampm == "pm" and hour < 12:
        hour += 12
    if ampm == "am" and hour == 12:
        hour = 0

    base = _local_now(settings).replace(second=0, microsecond=0)
    if when == "tomorrow":
        due = (base + timedelta(days=1)).replace(hour=hour, minute=minute)
    else:
        due = base.replace(hour=hour, minute=minute)
        if due <= base:
            due += timedelta(days=1)

    cleaned = RELATIVE_RE.sub("", text).strip(" ,.-")
    return cleaned, due


def parse_with_regex(text: str, settings: Settings) -> ParsedCapture | None:
    body = text.strip()
    if not body:
        return None

    if HELP_RE.match(body):
        return ParsedCapture(kind="help")

    if DIGEST_RE.match(body):
        return ParsedCapture(kind="digest")

    done_match = DONE_RE.match(body)
    if done_match:
        return ParsedCapture(kind="done", task_number=int(done_match.group(1)))

    list_match = LIST_RE.match(body)
    if list_match:
        bucket = (list_match.group(1) or "today").lower()
        return ParsedCapture(kind="list", status=bucket)

    for pattern, kind in ((TODO_RE, "todo"), (NOTE_RE, "note")):
        match = pattern.match(body)
        if not match:
            continue
        remainder = match.group(1).strip()
        title, due_at = _apply_relative_datetime(remainder, settings)
        status = "scheduled" if due_at else "inbox"
        return ParsedCapture(
            kind=kind,
            title=title,
            due_at=due_at,
            remind_at=due_at,
            status=status,
            raw_command=body,
        )

    return None


async def parse_capture(text: str, settings: Settings) -> ParsedCapture:
    regex_result = parse_with_regex(text, settings)
    if regex_result and regex_result.kind != "unknown":
        return regex_result

    ollama = OllamaClient(settings)
    now_iso = _local_now(settings).isoformat()
    llm_result = await ollama.parse_capture(text, now_iso)
    if llm_result:
        return llm_result

    if regex_result:
        return regex_result

    return ParsedCapture(kind="todo", title=text.strip(), status="inbox")
