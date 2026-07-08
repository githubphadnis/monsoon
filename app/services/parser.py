"""Command parsing — regex first, Ollama fallback."""

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.config import Settings
from app.integrations.ollama.client import OllamaClient
from app.schemas.capture import ParsedCapture

# --- Keyword patterns (case-insensitive) ---
# todo:     todo | to do | to-do
# note:     note
# done:     done | complete | finish | mark done N | mark N done
# list:     list | show | task(s) [bucket]
# digest:   digest | digest now | summary
# help:     help | ? | commands
# remind:   remind [me] [to] … | remember to …

TODO_RE = re.compile(r"^to[\s-]*do\s+(.+)$", re.IGNORECASE)
NOTE_RE = re.compile(r"^note\s+(.+)$", re.IGNORECASE)
REMIND_RE = re.compile(
    r"^remind(?:\s+me)?(?:\s+to)?\s+(.+)$|^remember(?:\s+to)?\s+(.+)$",
    re.IGNORECASE,
)
DONE_RE = re.compile(r"^(?:done|complete|finish|mark\s+done)\s+#?(\d+)\s*$", re.IGNORECASE)
DONE_MARK_RE = re.compile(r"^mark\s+#?(\d+)\s+done\s*$", re.IGNORECASE)
LIST_RE = re.compile(r"^(?:list|show|tasks?)(?:\s+(\w+))?\s*$", re.IGNORECASE)
DIGEST_RE = re.compile(r"^(?:digest(?:\s+now)?|summary)\s*$", re.IGNORECASE)
REFLECT_RE = re.compile(r"^reflect\s+(.+)$", re.IGNORECASE)
NOTE_ON_TASK_RE = re.compile(r"^note\s+#?(\d+)\s+(.+)$", re.IGNORECASE)
HELP_RE = re.compile(r"^(?:help|\?|commands)\s*$", re.IGNORECASE)

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


def _capture_from_match(match: re.Match[str], settings: Settings, *, kind: str, body: str) -> ParsedCapture:
    remainder = next(g for g in match.groups() if g is not None).strip()
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


def parse_with_regex(text: str, settings: Settings) -> ParsedCapture | None:
    body = text.strip()
    if not body:
        return None

    if HELP_RE.match(body):
        return ParsedCapture(kind="help")

    if DIGEST_RE.match(body):
        return ParsedCapture(kind="digest")

    reflect_match = REFLECT_RE.match(body)
    if reflect_match:
        return ParsedCapture(kind="reflect", reflect_topic=reflect_match.group(1).strip())

    done_match = DONE_RE.match(body) or DONE_MARK_RE.match(body)
    if done_match:
        return ParsedCapture(kind="done", task_number=int(done_match.group(1)))

    list_match = LIST_RE.match(body)
    if list_match:
        bucket = (list_match.group(1) or "today").lower()
        return ParsedCapture(kind="list", status=bucket)

    note_task_match = NOTE_ON_TASK_RE.match(body)
    if note_task_match:
        return ParsedCapture(
            kind="task_note",
            task_number=int(note_task_match.group(1)),
            title=note_task_match.group(2).strip(),
            raw_command=body,
        )

    for pattern, kind in ((TODO_RE, "todo"), (REMIND_RE, "todo"), (NOTE_RE, "note")):
        match = pattern.match(body)
        if match:
            return _capture_from_match(match, settings, kind=kind, body=body)

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
