"""Capture loop — parse WhatsApp text, persist tasks, reply."""

import logging
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.integrations.ollama.client import OllamaClient
from app.integrations.whatsapp.waha_client import WahaClient
from app.models import InboundMessage, OutboundMessage, Task, TaskEvent, User
from app.schemas.capture import ParsedCapture
from app.schemas.context import ContextSliceRequest
from app.services.context_slice import build_context_slice
from app.services.parser import parse_capture
from app.services.users import get_or_create_user
from app.services.workflowy_mirror import WorkFlowyMirrorService

logger = logging.getLogger("monsoon.capture")

HELP_TEXT = """monsoon — capture & remind

todo / to do <task>       create task
remind me to <task>       create task
note <text>               save a note
note <id> <text>          add context to task
done / complete <id>      mark complete
list / show today         open tasks
digest / summary          action digest (tasks + context)
reflect <topic>           what's active on a topic
ask anything              free-text questions (uses your context)
help / ?                  this message

Commands create tasks; other messages get an assistant reply."""

_URL_ONLY_RE = re.compile(r"^https?://\S+$", re.IGNORECASE)


class CaptureService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self._db = db
        self._settings = settings
        self._waha = WahaClient(settings)
        self._ollama = OllamaClient(settings)
        self._workflowy = WorkFlowyMirrorService(db, settings)

    async def handle_text(
        self,
        *,
        source_message_id: str,
        chat_id: str,
        sender_id: str | None = None,
        sender_phone: str | None = None,
        text: str,
        raw_payload: dict,
    ) -> str | None:
        existing = self._db.scalar(
            select(InboundMessage).where(InboundMessage.source_message_id == source_message_id)
        )
        if existing:
            logger.info("Duplicate webhook ignored: %s", source_message_id)
            return None

        resolved_sender = sender_id or chat_id
        inbound = InboundMessage(
            source="whatsapp",
            source_message_id=source_message_id,
            sender_id=resolved_sender,
            chat_id=chat_id,
            raw_payload=raw_payload,
            parsed_text=text,
            status="processing",
        )
        self._db.add(inbound)

        phone = sender_phone or resolved_sender.split("@", 1)[0]
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

        if parsed.kind == "reflect":
            return await self._reflect(user, parsed.reflect_topic)

        if parsed.kind == "ask":
            return await self._ask(user, parsed.title or parsed.raw_command or "")

        if parsed.kind == "list":
            return self._list_tasks(user, parsed.status or "today")

        if parsed.kind == "done":
            return await self._complete_task(user, parsed.task_number)

        if parsed.kind == "task_note":
            return await self._append_task_note(user, parsed, source_message_id)

        if parsed.kind in {"todo", "note"} and parsed.title:
            return await self._create_task(user, parsed, source_message_id)

        if parsed.title and parsed.kind != "unknown":
            return await self._create_task(user, parsed, source_message_id)

        return await self._ask(user, parsed.raw_command or parsed.title or "")

    def _now_iso(self) -> str:
        tz = ZoneInfo(self._settings.app_timezone)
        return datetime.now(tz).isoformat()

    def _context_bundle(self, user: User, topic: str | None = None) -> str:
        """Build LLM context — tasks/email/WA only (no entity dumps)."""
        slice_ = build_context_slice(
            self._db,
            self._settings,
            ContextSliceRequest(user_id=user.id, topic=topic),
        )
        parts: list[str] = []
        if slice_.tasks_text:
            parts.append(f"## Tasks\n{slice_.tasks_text}")
        if slice_.task_context_text:
            parts.append(f"## Task Context\n{slice_.task_context_text}")
        if slice_.emails_text:
            parts.append(f"## Email\n{slice_.emails_text}")
        if slice_.wa_messages_text:
            parts.append(f"## WhatsApp\n{slice_.wa_messages_text}")
        # Intentionally omit ## Entities — models regurgitate phone/email lists.
        return "\n\n".join(parts) if parts else "No indexed context yet."

    def _next_display_number(self, user_id) -> int:
        current = self._db.scalar(
            select(func.max(Task.display_number)).where(Task.user_id == user_id)
        )
        return int(current or 0) + 1

    @staticmethod
    def _short_title(title: str, limit: int = 60) -> str:
        cleaned = title.strip()
        if len(cleaned) <= limit:
            return cleaned
        return cleaned[: limit - 1].rstrip() + "…"

    async def _create_task(self, user: User, parsed: ParsedCapture, source_message_id: str) -> str:
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

        try:
            await self._workflowy.push_task_created(task, user=user)
        except Exception:
            logger.exception("WorkFlowy mirror failed for task #%s", display_number)

        due_part = ""
        if parsed.due_at:
            tz = ZoneInfo(self._settings.app_timezone)
            local = parsed.due_at.astimezone(tz) if parsed.due_at.tzinfo else parsed.due_at
            due_part = f" · {local.strftime('%a %d %b %H:%M')}"

        return f"Saved · #{display_number} {self._short_title(task.title)}{due_part}"

    async def _append_task_note(
        self, user: User, parsed: ParsedCapture, source_message_id: str
    ) -> str:
        if not parsed.task_number or not parsed.title:
            return "Usage: `note <id> <text>`"
        task = self._db.scalar(
            select(Task).where(Task.user_id == user.id, Task.display_number == parsed.task_number)
        )
        if not task:
            return f"No task #{parsed.task_number} found."

        try:
            await self._workflowy.push_context_item(
                task,
                parsed.title,
                source="whatsapp",
                source_ref=source_message_id,
            )
        except Exception:
            logger.exception("WorkFlowy context push failed for task #%s", parsed.task_number)

        self._db.add(
            TaskEvent(
                task_id=task.id,
                event_type="context_from_whatsapp",
                payload={"body": parsed.title, "source_message_id": source_message_id},
            )
        )
        return f"Noted · #{parsed.task_number} {self._short_title(parsed.title)}"

    async def _complete_task(self, user: User, task_number: int | None) -> str:
        if not task_number:
            return "Usage: `done <id>` or `complete <id>`"
        task = self._db.scalar(
            select(Task).where(Task.user_id == user.id, Task.display_number == task_number)
        )
        if not task:
            return f"No task #{task_number} found."
        if task.status == "done":
            return f"Already done · #{task_number}"
        task.status = "done"
        self._db.add(
            TaskEvent(task_id=task.id, event_type="completed_from_whatsapp", payload={})
        )

        try:
            await self._workflowy.complete_task(task)
        except Exception:
            logger.exception("WorkFlowy complete failed for task #%s", task_number)

        return f"Done · #{task_number} {self._short_title(task.title)}"

    def _list_tasks(self, user: User, bucket: str) -> str:
        tz = ZoneInfo(self._settings.app_timezone)
        today = datetime.now(tz).date()
        query = select(Task).where(Task.user_id == user.id, Task.status != "done")
        tasks = list(self._db.scalars(query.order_by(Task.display_number.desc()).limit(40)))

        if bucket == "today":
            tasks = [
                t
                for t in tasks
                if t.status in {"inbox", "today", "scheduled"}
                and (t.due_at is None or t.due_at.astimezone(tz).date() <= today)
            ]
        elif bucket == "tomorrow":
            tomorrow = today.fromordinal(today.toordinal() + 1)
            tasks = [
                t
                for t in tasks
                if t.status != "done"
                and (
                    (t.due_at is not None and t.due_at.astimezone(tz).date() <= tomorrow)
                    or t.status in {"inbox", "today", "scheduled"}
                )
            ]

        visible = [t for t in tasks if not _URL_ONLY_RE.match((t.title or "").strip())]
        if not visible:
            return f"No tasks for `{bucket}`."

        lines = [f"*{bucket}* ({len(visible)})"]
        for task in reversed(visible[:12]):
            due = ""
            if task.due_at:
                due = f" — {task.due_at.astimezone(tz).strftime('%d %b %H:%M')}"
            lines.append(f"#{task.display_number} {task.title}{due}")
        return "\n".join(lines)

    def _sql_digest(self, user: User) -> str:
        tz = ZoneInfo(self._settings.app_timezone)
        open_tasks = list(
            self._db.scalars(
                select(Task)
                .where(Task.user_id == user.id, Task.status != "done")
                .order_by(Task.display_number.desc())
                .limit(15)
            )
        )
        visible = [t for t in open_tasks if not _URL_ONLY_RE.match((t.title or "").strip())]
        if not visible:
            return "Nothing open right now. Inbox zero?"
        lines = ["*Digest*"]
        for task in reversed(visible[:10]):
            due = ""
            if task.due_at:
                due = f" — {task.due_at.astimezone(tz).strftime('%d %b %H:%M')}"
            lines.append(f"{task.title} [{task.status}]{due}")
        return "\n".join(lines)

    async def _digest(self, user: User) -> str:
        context_text = self._context_bundle(user)
        llm_text = await self._ollama.generate_digest(
            context_text=context_text,
            now_iso=self._now_iso(),
        )
        if llm_text:
            return llm_text.strip()
        return self._sql_digest(user)

    async def _reflect(self, user: User, topic: str | None) -> str:
        if not topic:
            return "Usage: `reflect <topic>`"
        context_text = self._context_bundle(user, topic=topic)
        llm_text = await self._ollama.generate_reflect(
            topic=topic,
            context_text=context_text,
            now_iso=self._now_iso(),
        )
        if llm_text:
            return llm_text.strip()
        return (
            f"Couldn't reflect on `{topic}` right now (assistant offline). "
            "Try again shortly, or send `digest`."
        )

    async def _ask(self, user: User, question: str) -> str:
        q = (question or "").strip()
        if not q:
            return "Ask me anything about your tasks or context — or send `help`."
        context_text = self._context_bundle(user)
        llm_text = await self._ollama.generate_ask(
            question=q,
            context_text=context_text,
            now_iso=self._now_iso(),
        )
        if llm_text:
            return llm_text.strip()
        return (
            "Couldn't reach the assistant just now. "
            "Try `digest`, `reflect <topic>`, or `todo …`."
        )

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
            outbound.provider_message_id = str(result.get("id", "") or "") or None
            self._db.commit()
        except Exception as exc:
            outbound.status = "error"
            outbound.error = str(exc)
            logger.exception("Failed to send WhatsApp reply")
        self._db.flush()
