"""Capture loop — parse WhatsApp text, persist tasks, reply."""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.integrations.whatsapp.waha_client import WahaClient
from app.models import InboundMessage, OutboundMessage, Task, TaskEvent, User
from app.schemas.capture import ParsedCapture
from app.services.parser import parse_capture
from app.services.users import get_or_create_user

logger = logging.getLogger("monsoon.capture")

HELP_TEXT = """monsoon — capture & remind

todo <task>          create task
note <text>          save a note
done <id>            mark complete
list today           open tasks
digest now           summary (stub)
help                 this message

Free text works too — I'll parse it."""


class CaptureService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self._db = db
        self._settings = settings
        self._waha = WahaClient(settings)

    async def handle_text(
        self,
        *,
        source_message_id: str,
        chat_id: str,
        sender_id: str,
        text: str,
        raw_payload: dict,
    ) -> str | None:
        existing = self._db.scalar(
            select(InboundMessage).where(InboundMessage.source_message_id == source_message_id)
        )
        if existing:
            logger.info("Duplicate webhook ignored: %s", source_message_id)
            return None

        inbound = InboundMessage(
            source="whatsapp",
            source_message_id=source_message_id,
            sender_id=sender_id,
            chat_id=chat_id,
            raw_payload=raw_payload,
            parsed_text=text,
            status="processing",
        )
        self._db.add(inbound)

        phone = sender_id.split("@", 1)[0]
        user = get_or_create_user(self._db, phone, self._settings)

        try:
            parsed = await parse_capture(text, self._settings)
            reply = await self._dispatch(user, parsed, source_message_id)
            inbound.status = "processed"
        except Exception as exc:
            inbound.status = "error"
            inbound.error = str(exc)
            reply = "Something went wrong saving that. Try again?"
            logger.exception("Capture failed for %s", source_message_id)

        if reply:
            await self._send_reply(chat_id, reply)
        self._db.commit()
        return reply

    async def _dispatch(self, user: User, parsed: ParsedCapture, source_message_id: str) -> str:
        if parsed.kind == "help":
            return HELP_TEXT

        if parsed.kind == "digest":
            return await self._digest(user)

        if parsed.kind == "list":
            return self._list_tasks(user, parsed.status or "today")

        if parsed.kind == "done":
            return self._complete_task(user, parsed.task_number)

        if parsed.kind in {"todo", "note"} and parsed.title:
            return self._create_task(user, parsed, source_message_id)

        if parsed.title:
            return self._create_task(user, parsed, source_message_id)

        return "I didn't catch that. Send `help` for commands."

    def _next_display_number(self, user_id) -> int:
        current = self._db.scalar(
            select(func.max(Task.display_number)).where(Task.user_id == user_id)
        )
        return int(current or 0) + 1

    def _create_task(self, user: User, parsed: ParsedCapture, source_message_id: str) -> str:
        display_number = self._next_display_number(user.id)
        status = parsed.status or ("scheduled" if parsed.due_at else "inbox")
        task = Task(
            user_id=user.id,
            display_number=display_number,
            title=parsed.title or "Untitled",
            notes=parsed.notes,
            status=status,
            priority=parsed.priority or "normal",
            due_at=parsed.due_at,
            remind_at=parsed.remind_at or parsed.due_at,
            source="whatsapp",
            source_message_id=source_message_id,
        )
        self._db.add(task)
        self._db.flush()
        self._db.add(
            TaskEvent(
                task_id=task.id,
                event_type="created_from_whatsapp",
                payload={"parsed": parsed.model_dump(mode="json")},
            )
        )

        due_part = ""
        if parsed.due_at:
            tz = ZoneInfo(self._settings.app_timezone)
            local = parsed.due_at.astimezone(tz) if parsed.due_at.tzinfo else parsed.due_at
            due_part = f" Reminder: {local.strftime('%a %d %b %H:%M')}."

        kind_label = "Note" if parsed.kind == "note" else "Task"
        return f"{kind_label} #{display_number} created: {task.title}.{due_part}"

    def _complete_task(self, user: User, task_number: int | None) -> str:
        if not task_number:
            return "Usage: `done <id>`"
        task = self._db.scalar(
            select(Task).where(Task.user_id == user.id, Task.display_number == task_number)
        )
        if not task:
            return f"No task #{task_number} found."
        if task.status == "done":
            return f"Task #{task_number} is already done."
        task.status = "done"
        self._db.add(
            TaskEvent(task_id=task.id, event_type="completed_from_whatsapp", payload={})
        )
        return f"Done — #{task_number}: {task.title}"

    def _list_tasks(self, user: User, bucket: str) -> str:
        tz = ZoneInfo(self._settings.app_timezone)
        today = datetime.now(tz).date()
        query = select(Task).where(Task.user_id == user.id, Task.status != "done")
        tasks = list(self._db.scalars(query.order_by(Task.display_number.desc()).limit(20)))

        if bucket == "today":
            tasks = [
                t
                for t in tasks
                if t.status in {"inbox", "today", "scheduled"}
                and (t.due_at is None or t.due_at.astimezone(tz).date() <= today)
            ]

        if not tasks:
            return f"No tasks for `{bucket}`."

        lines = [f"*{bucket}* ({len(tasks)})"]
        for task in reversed(tasks[:10]):
            due = ""
            if task.due_at:
                due = f" — {task.due_at.astimezone(tz).strftime('%d %b %H:%M')}"
            lines.append(f"#{task.display_number} {task.title}{due}")
        return "\n".join(lines)

    async def _digest(self, user: User) -> str:
        open_tasks = list(
            self._db.scalars(
                select(Task)
                .where(Task.user_id == user.id, Task.status != "done")
                .order_by(Task.display_number.desc())
                .limit(10)
            )
        )
        if not open_tasks:
            return "Nothing open right now. Inbox zero?"
        lines = ["*Digest*"]
        for task in reversed(open_tasks):
            lines.append(f"#{task.display_number} {task.title} [{task.status}]")
        return "\n".join(lines)

    async def _send_reply(self, chat_id: str, text: str) -> None:
        outbound = OutboundMessage(
            channel="whatsapp",
            recipient=chat_id,
            message_body=text,
            status="pending",
        )
        self._db.add(outbound)
        self._db.flush()
        try:
            result = await self._waha.send_text(chat_id, text)
            outbound.status = "sent"
            outbound.sent_at = datetime.now(ZoneInfo("UTC"))
            outbound.provider_message_id = str(result.get("id", "")) or None
        except Exception as exc:
            outbound.status = "error"
            outbound.error = str(exc)
            logger.exception("Failed to send WhatsApp reply")
        self._db.flush()
