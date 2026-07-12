"""Capture loop — parse WhatsApp text, persist tasks, reply."""

import asyncio
import logging
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
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
        self._pending_workflowy_tasks: list[tuple[Task, User]] = []

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

        # Claim this message id before heavy work so a twin webhook cannot race.
        try:
            self._db.flush()
        except IntegrityError:
            self._db.rollback()
            logger.info("Duplicate webhook ignored (flush race): %s", source_message_id)
            return None

        parsed: ParsedCapture | None = None
        try:
            parsed = await parse_capture(text, self._settings)
            reply = await self._dispatch(user, parsed, source_message_id, chat_id=chat_id)
            inbound.status = "processed"
        except Exception as exc:
            inbound.status = "error"
            inbound.error = str(exc)
            reply = "Something went wrong saving that. Try again?"
            logger.exception("Capture failed for %s", source_message_id)

        if reply:
            await self._send_reply(chat_id, reply)
            logger.info(
                "Capture reply sent chat_id=%s phone=%s kind=%s",
                chat_id,
                phone,
                parsed.kind if parsed else "error",
            )
        await self._flush_pending_workflowy()
        self._db.commit()
        return reply

    async def _flush_pending_workflowy(self) -> None:
        pending = list(self._pending_workflowy_tasks)
        self._pending_workflowy_tasks.clear()
        for task, user in pending:
            try:
                await asyncio.wait_for(
                    self._workflowy.push_task_created(task, user=user),
                    timeout=12.0,
                )
            except TimeoutError:
                logger.warning(
                    "WorkFlowy mirror timed out for task #%s", task.display_number
                )
            except Exception:
                logger.exception(
                    "WorkFlowy mirror failed for task #%s", task.display_number
                )

    async def _dispatch(
        self,
        user: User,
        parsed: ParsedCapture,
        source_message_id: str,
        *,
        chat_id: str,
    ) -> str:
        if parsed.kind == "help":
            return HELP_TEXT

        if parsed.kind == "digest":
            return await self._digest(user, chat_id=chat_id)

        if parsed.kind == "reflect":
            return await self._reflect(user, parsed.reflect_topic, chat_id=chat_id)

        if parsed.kind == "ask":
            return await self._ask(
                user, parsed.title or parsed.raw_command or "", chat_id=chat_id
            )

        if parsed.kind == "list":
            return self._list_tasks(user, parsed.status or "today", chat_id=chat_id)

        if parsed.kind == "done":
            return await self._complete_task(user, parsed.task_number)

        if parsed.kind == "task_note":
            return await self._append_task_note(user, parsed, source_message_id)

        if parsed.kind in {"todo", "note"} and parsed.title:
            return await self._create_task(user, parsed, source_message_id)

        if parsed.title and parsed.kind != "unknown":
            return await self._create_task(user, parsed, source_message_id)

        return await self._ask(
            user, parsed.raw_command or parsed.title or "", chat_id=chat_id
        )

    def _now_iso(self) -> str:
        tz = ZoneInfo(self._settings.app_timezone)
        return datetime.now(tz).isoformat()

    def _is_shared(self, chat_id: str) -> bool:
        from app.services.sender_identity import is_shared_chat

        return is_shared_chat(chat_id, self._settings)

    def _family_users(self) -> list[User]:
        phones = self._settings.allowed_numbers_set
        if not phones:
            return []
        return list(
            self._db.scalars(select(User).where(User.phone_number.in_(phones)))
        )

    def _owner_label(self, owner: User) -> str:
        phone = owner.phone_number or "?"
        return phone[-4:] if len(phone) >= 4 else phone

    def _wa_lines_for_chat(self, chat_id: str, *, limit: int = 30) -> list[str]:
        """Recent indexed WA lines from one conversation (group or 1:1)."""
        from app.models import WaChat, WaMessage
        from app.services.outbound_guard import is_bot_reply_text
        from app.services.sender_identity import chat_id_aliases

        aliases = chat_id_aliases(chat_id)
        session = self._settings.waha_session
        rows = self._db.execute(
            select(WaMessage, WaChat.name)
            .join(WaChat, WaMessage.chat_uuid == WaChat.id)
            .where(
                WaMessage.session == session,
                WaMessage.chat_id.in_(aliases),
                or_(WaMessage.from_me.is_(False), WaMessage.from_me.is_(None)),
            )
            .order_by(WaMessage.message_ts.desc().nullslast(), WaMessage.indexed_at.desc())
            .limit(limit * 2)
        ).all()
        lines: list[str] = []
        for msg, chat_name in rows:
            body = (msg.body or "").strip()
            if not body or is_bot_reply_text(body):
                continue
            who = msg.from_id or "?"
            ts = (
                msg.message_ts.strftime("%Y-%m-%d %H:%M")
                if msg.message_ts
                else ""
            )
            label = chat_name or chat_id
            lines.append(f"[{label}] {who} {ts} {body}".strip())
            if len(lines) >= limit:
                break
        return lines

    def _tasks_for_scope(self, user: User, chat_id: str) -> list[tuple[User, Task]]:
        """Personal: only this user. Shared chat: all allowlisted family users."""
        if self._is_shared(chat_id):
            owners = self._family_users() or [user]
        else:
            owners = [user]
        owner_by_id = {o.id: o for o in owners}
        tasks = list(
            self._db.scalars(
                select(Task)
                .where(Task.user_id.in_(owner_by_id.keys()), Task.status != "done")
                .order_by(Task.display_number.desc())
                .limit(40)
            )
        )
        return [(owner_by_id[t.user_id], t) for t in tasks if t.user_id in owner_by_id]

    def _context_bundle(
        self, user: User, topic: str | None = None, *, chat_id: str | None = None
    ) -> str:
        """LLM context scoped to the conversation.

        Personal chats: this user's tasks/notes only (no global email/WA leak).
        Shared family chats: all members' tasks + WA lines from that group.
        """
        chat = chat_id or ""
        if self._is_shared(chat):
            parts: list[str] = []
            scoped = self._tasks_for_scope(user, chat)
            if scoped:
                tz = ZoneInfo(self._settings.app_timezone)
                lines = []
                for owner, task in scoped[:25]:
                    due = ""
                    if task.due_at:
                        due = f" due:{task.due_at.astimezone(tz).strftime('%Y-%m-%d %H:%M')}"
                    lines.append(
                        f"{self._owner_label(owner)}: {task.title} [{task.status}]{due}"
                    )
                parts.append("## Family tasks\n" + "\n".join(lines))
            wa_lines = self._wa_lines_for_chat(chat, limit=25)
            if topic:
                t = topic.lower()
                wa_lines = [ln for ln in wa_lines if t in ln.lower()][:20]
            if wa_lines:
                parts.append("## This group (WhatsApp)\n" + "\n".join(wa_lines))
            return "\n\n".join(parts) if parts else "No shared context in this group yet."

        # Personal — tasks only (prevents dad's atlas leaking into son's digest/ask)
        slice_ = build_context_slice(
            self._db,
            self._settings,
            ContextSliceRequest(user_id=user.id, topic=topic, max_chars=6000),
        )
        parts = []
        if slice_.tasks_text:
            parts.append(f"## Tasks\n{slice_.tasks_text}")
        if slice_.task_context_text:
            parts.append(f"## Task Context\n{slice_.task_context_text}")
        return "\n\n".join(parts) if parts else "No open tasks yet."

    def _digest_context_bundle(self, user: User, *, chat_id: str) -> str:
        """Digest input: personal = own tasks only; shared = family tasks (+ group WA)."""
        if self._is_shared(chat_id):
            return self._context_bundle(user, chat_id=chat_id)

        slice_ = build_context_slice(
            self._db,
            self._settings,
            ContextSliceRequest(user_id=user.id, topic=None, max_chars=4000),
        )
        parts: list[str] = []
        if slice_.tasks_text:
            parts.append(
                "## Open tasks (PRIMARY — build the digest from these only)\n"
                + slice_.tasks_text
            )
        if slice_.task_context_text:
            note_lines = slice_.task_context_text.splitlines()[:12]
            parts.append("## Notes on those tasks\n" + "\n".join(note_lines))
        # No global Email/WhatsApp — that leaked other people's atlas into digests.
        return "\n\n".join(parts) if parts else "No open tasks yet."

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

        due_part = ""
        if parsed.due_at:
            tz = ZoneInfo(self._settings.app_timezone)
            local = parsed.due_at.astimezone(tz) if parsed.due_at.tzinfo else parsed.due_at
            due_part = f" · {local.strftime('%a %d %b %H:%M')}"

        reply = f"Saved · #{display_number} {self._short_title(task.title)}{due_part}"
        # Mirror after WhatsApp ack (see _flush_pending_workflowy) so groups aren't blocked.
        self._pending_workflowy_tasks.append((task, user))
        return reply

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

    def _list_tasks(self, user: User, bucket: str, *, chat_id: str) -> str:
        tz = ZoneInfo(self._settings.app_timezone)
        today = datetime.now(tz).date()
        scoped = self._tasks_for_scope(user, chat_id)
        tasks = [(o, t) for o, t in scoped]

        if bucket == "today":
            tasks = [
                (o, t)
                for o, t in tasks
                if t.status in {"inbox", "today", "scheduled"}
                and (t.due_at is None or t.due_at.astimezone(tz).date() <= today)
            ]
        elif bucket == "tomorrow":
            tomorrow = today.fromordinal(today.toordinal() + 1)
            tasks = [
                (o, t)
                for o, t in tasks
                if t.status != "done"
                and (
                    (t.due_at is not None and t.due_at.astimezone(tz).date() <= tomorrow)
                    or t.status in {"inbox", "today", "scheduled"}
                )
            ]

        visible = [
            (o, t) for o, t in tasks if not _URL_ONLY_RE.match((t.title or "").strip())
        ]
        if not visible:
            return f"No tasks for `{bucket}`."

        shared = self._is_shared(chat_id)
        header = f"*family {bucket}*" if shared else f"*{bucket}*"
        lines = [f"{header} ({len(visible)})"]
        for owner, task in reversed(visible[:12]):
            due = ""
            if task.due_at:
                due = f" — {task.due_at.astimezone(tz).strftime('%d %b %H:%M')}"
            prefix = f"{self._owner_label(owner)} " if shared else ""
            lines.append(f"{prefix}#{task.display_number} {task.title}{due}")
        return "\n".join(lines)

    def _sql_digest(self, user: User, *, chat_id: str) -> str:
        tz = ZoneInfo(self._settings.app_timezone)
        scoped = self._tasks_for_scope(user, chat_id)
        visible = [
            (o, t) for o, t in scoped if not _URL_ONLY_RE.match((t.title or "").strip())
        ][:10]
        if not visible:
            return "Nothing open right now. Inbox zero?"
        shared = self._is_shared(chat_id)
        lines = ["*Family — open tasks*" if shared else "*Today — open tasks*"]
        for owner, task in reversed(visible):
            due = ""
            if task.due_at:
                due = f" — {task.due_at.astimezone(tz).strftime('%d %b %H:%M')}"
            who = f"{self._owner_label(owner)}: " if shared else ""
            lines.append(f"• {who}{task.title}{due}")
        lines.append("Next: pick the top one and finish it.")
        return "\n".join(lines)

    async def _digest(self, user: User, *, chat_id: str) -> str:
        context_text = self._digest_context_bundle(user, chat_id=chat_id)
        llm_text = await self._ollama.generate_digest(
            context_text=context_text,
            now_iso=self._now_iso(),
        )
        if llm_text:
            return llm_text.strip()
        return self._sql_digest(user, chat_id=chat_id)

    async def _reflect(
        self, user: User, topic: str | None, *, chat_id: str
    ) -> str:
        if not topic:
            return "Usage: `reflect <topic>`"
        context_text = self._context_bundle(user, topic=topic, chat_id=chat_id)
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

    async def _ask(self, user: User, question: str, *, chat_id: str) -> str:
        q = (question or "").strip()
        if not q:
            return "Ask me anything about your tasks or context — or send `help`."
        context_text = self._context_bundle(user, chat_id=chat_id)
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
