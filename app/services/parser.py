"""Command parsing — regex first, Ollama fallback, ask for free-text chat."""

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

TODO_RE = re.compile(r"^to[\s-]*do(?:\s*:|\s+)\s*(.+)$", re.IGNORECASE)
NOTE_RE = re.compile(r"^note(?:\s*:|\s+)\s*(.+)$", re.IGNORECASE)
REMIND_RE = re.compile(
    r"^remind(?:\s+me)?(?:\s+to)?\s+(.+)$|^remember(?:\s+to)?\s+(.+)$",
    re.IGNORECASE,
)
DONE_RE = re.compile(r"^(?:done|complete|finish|mark\s+done)\s+#?(\d+)\s*$", re.IGNORECASE)
DONE_MARK_RE = re.compile(r"^mark\s+#?(\d+)\s+done\s*$", re.IGNORECASE)
DELETE_RE = re.compile(r"^(?:delete|remove|cancel)\s+#?(\d+)\s*$", re.IGNORECASE)
LIST_RE = re.compile(r"^(?:list|show|tasks?)(?:\s+(\w+))?\s*$", re.IGNORECASE)
DIGEST_RE = re.compile(r"^(?:digest(?:\s+now)?|summary)\s*$", re.IGNORECASE)
REFLECT_RE = re.compile(r"^reflect\s+(.+)$", re.IGNORECASE)
NOTE_ON_TASK_RE = re.compile(r"^note\s+#?(\d+)\s+(.+)$", re.IGNORECASE)
HELP_RE = re.compile(r"^(?:help|\?|commands)\s*$", re.IGNORECASE)
# Leading @alias …  or  todo @alias …
ASSIGN_TODO_RE = re.compile(
    r"^(?:to[\s-]*do(?:\s*:|\s+)|assign(?:\s*:|\s+))?@([A-Za-z][\w.-]*)\s+(.+)$",
    re.IGNORECASE,
)
INLINE_ASSIGNEE_RE = re.compile(r"@([A-Za-z][\w.-]*)")

QUESTION_RE = re.compile(
    r"(?:\?$)|^(?:what|why|how|when|where|who|which|elaborate|explain|tell\s+me|"
    r"ok\s+what|what\s+about|can\s+you|could\s+you|please\s+(?:explain|tell|summarize))\b",
    re.IGNORECASE,
)

_COMMAND_KINDS = frozenset(
    {"todo", "note", "task_note", "done", "delete", "list", "digest", "reflect", "help"}
)

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
    title, due_at, assignee = _split_assignee_and_due(remainder, settings)
    status = "scheduled" if due_at else "inbox"
    return ParsedCapture(
        kind=kind,
        title=title,
        due_at=due_at,
        remind_at=due_at,
        status=status,
        assignee_alias=assignee,
        raw_command=body,
    )


def _split_assignee_and_due(
    text: str, settings: Settings
) -> tuple[str, datetime | None, str | None]:
    assignee: str | None = None
    cleaned = text
    found = INLINE_ASSIGNEE_RE.search(cleaned)
    if found:
        assignee = found.group(1).lower()
        cleaned = INLINE_ASSIGNEE_RE.sub("", cleaned, count=1).strip(" ,.-")
    title, due_at = _apply_relative_datetime(cleaned, settings)
    return title, due_at, assignee


def looks_like_question(text: str) -> bool:
    body = text.strip()
    if not body:
        return False
    return bool(QUESTION_RE.search(body))


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

    delete_match = DELETE_RE.match(body)
    if delete_match:
        return ParsedCapture(kind="delete", task_number=int(delete_match.group(1)))

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

    assign_lead = ASSIGN_TODO_RE.match(body)
    if assign_lead:
        alias = assign_lead.group(1).lower()
        remainder = assign_lead.group(2).strip()
        title, due_at = _apply_relative_datetime(remainder, settings)
        return ParsedCapture(
            kind="todo",
            title=title,
            due_at=due_at,
            remind_at=due_at,
            status="scheduled" if due_at else "inbox",
            assignee_alias=alias,
            raw_command=body,
        )

    for pattern, kind in ((TODO_RE, "todo"), (REMIND_RE, "todo"), (NOTE_RE, "note")):
        match = pattern.match(body)
        if match:
            return _capture_from_match(match, settings, kind=kind, body=body)

    return None


def _as_ask(text: str) -> ParsedCapture:
    return ParsedCapture(kind="ask", title=text.strip(), raw_command=text.strip())


async def parse_capture(text: str, settings: Settings) -> ParsedCapture:
    body = text.strip()
    regex_result = parse_with_regex(body, settings)
    if regex_result and regex_result.kind != "unknown":
        return regex_result

    if looks_like_question(body):
        return _as_ask(body)

    ollama = OllamaClient(settings)
    now_iso = _local_now(settings).isoformat()
    llm_result = await ollama.parse_capture(body, now_iso)
    if llm_result and llm_result.kind in _COMMAND_KINDS:
        return llm_result

    # Free text → conversational ask (do not auto-create junk todos).
    return _as_ask(body)
