"""Assemble bounded SQL-backed context for LLM calls."""

from __future__ import annotations

from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import ExtractedEntity, Task, WaChat, WaMessage
from app.schemas.context import ContextSlice, ContextSliceRequest


def build_context_slice(
    db: Session, settings: Settings, request: ContextSliceRequest
) -> ContextSlice:
    tz = ZoneInfo(settings.app_timezone)
    task_lines = _fetch_task_lines(db, request.user_id, tz)
    wa_lines, message_ids = _fetch_wa_lines(db, settings, request.topic)
    entity_lines = _fetch_entity_lines(db, message_ids, request.topic)

    task_lines, wa_lines, entity_lines = _apply_char_budget(
        task_lines, wa_lines, entity_lines, request.max_chars
    )

    tasks_text = "\n".join(task_lines)
    wa_messages_text = "\n".join(wa_lines)
    entities_text = "\n".join(entity_lines)

    return ContextSlice(
        tasks_text=tasks_text,
        wa_messages_text=wa_messages_text,
        entities_text=entities_text,
        topic=request.topic,
        char_count=len(tasks_text) + len(wa_messages_text) + len(entities_text),
    )


def _fetch_task_lines(db: Session, user_id, tz: ZoneInfo) -> list[str]:
    tasks = list(
        db.scalars(
            select(Task)
            .where(Task.user_id == user_id, Task.status != "done")
            .order_by(Task.display_number.desc())
            .limit(20)
        )
    )
    return [_format_task_line(task, tz) for task in tasks]


def _format_task_line(task: Task, tz: ZoneInfo) -> str:
    parts = [f"#{task.display_number} {task.title} [{task.status}]"]
    if task.due_at:
        due = task.due_at.astimezone(tz).strftime("%Y-%m-%d %H:%M")
        parts.append(f"due:{due}")
    if task.notes:
        parts.append(f"notes:{task.notes}")
    return " ".join(parts)


def _fetch_wa_lines(
    db: Session, settings: Settings, topic: str | None
) -> tuple[list[str], list[str]]:
    session = settings.waha_session
    has_messages = db.scalar(
        select(func.count()).select_from(WaMessage).where(WaMessage.session == session)
    )
    if not has_messages:
        return [], []

    stmt = (
        select(WaMessage, WaChat.name)
        .join(WaChat, WaMessage.chat_uuid == WaChat.id)
        .where(WaMessage.session == session)
    )
    if topic:
        pattern = f"%{topic}%"
        stmt = stmt.where(
            or_(
                WaMessage.body.ilike(pattern),
                WaChat.name.ilike(pattern),
            )
        )

    rows = db.execute(
        stmt.order_by(WaMessage.message_ts.desc().nullslast(), WaMessage.indexed_at.desc()).limit(30)
    ).all()

    lines: list[str] = []
    message_ids: list[str] = []
    for msg, chat_name in rows:
        message_ids.append(msg.waha_message_id)
        lines.append(_format_wa_line(msg, chat_name))
    return lines, message_ids


def _format_wa_line(msg: WaMessage, chat_name: str | None) -> str:
    label = chat_name or msg.chat_id
    body = (msg.body or "").strip()
    if msg.message_ts:
        ts = msg.message_ts.strftime("%Y-%m-%d %H:%M")
        return f"[{label}] {ts} {body}".strip()
    return f"[{label}] {body}".strip()


def _fetch_entity_lines(
    db: Session, message_ids: list[str], topic: str | None
) -> list[str]:
    if topic:
        if not message_ids:
            return []
        stmt = (
            select(ExtractedEntity)
            .where(
                ExtractedEntity.source_type == "wa_message",
                ExtractedEntity.source_id.in_(message_ids),
            )
            .order_by(ExtractedEntity.created_at.desc())
            .limit(20)
        )
    else:
        stmt = select(ExtractedEntity).order_by(ExtractedEntity.created_at.desc()).limit(20)

    entities = list(db.scalars(stmt))
    return [_format_entity_line(entity) for entity in entities]


def _format_entity_line(entity: ExtractedEntity) -> str:
    return f"{entity.entity_type}:{entity.value}"


def _section_char_count(
    task_lines: list[str], wa_lines: list[str], entity_lines: list[str]
) -> int:
    return sum(len("\n".join(lines)) for lines in (task_lines, wa_lines, entity_lines) if lines)


def _apply_char_budget(
    task_lines: list[str],
    wa_lines: list[str],
    entity_lines: list[str],
    max_chars: int,
) -> tuple[list[str], list[str], list[str]]:
    """Drop oldest lines section-by-section until within max_chars."""
    sections: list[list[str]] = [entity_lines, wa_lines, task_lines]

    while _section_char_count(task_lines, wa_lines, entity_lines) > max_chars:
        trimmed = False
        for section in sections:
            if not section:
                continue
            section.pop()
            trimmed = True
            if _section_char_count(task_lines, wa_lines, entity_lines) <= max_chars:
                return task_lines, wa_lines, entity_lines
        if not trimmed:
            break

    return task_lines, wa_lines, entity_lines
