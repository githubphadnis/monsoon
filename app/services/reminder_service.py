"""Due reminder delivery — remind_at → WhatsApp outbound."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.integrations.whatsapp.waha_client import WahaClient
from app.models import OutboundMessage, Task, TaskEvent, User

logger = logging.getLogger("monsoon.reminders")


@dataclass
class ReminderStats:
    due_found: int = 0
    sent: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


class ReminderService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self._db = db
        self._settings = settings
        self._waha = WahaClient(settings)

    async def send_due(self, *, now: datetime | None = None, limit: int = 20) -> ReminderStats:
        """Send reminders for tasks with remind_at <= now and status != done.

        Idempotency: after a successful send we clear `remind_at` so container
        restarts cannot re-fire the same reminder.
        """
        stats = ReminderStats()
        now = now or datetime.now(UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)

        tasks = list(
            self._db.scalars(
                select(Task)
                .where(
                    Task.status != "done",
                    Task.remind_at.is_not(None),
                    Task.remind_at <= now,
                )
                .order_by(Task.remind_at.asc())
                .limit(limit)
            )
        )
        stats.due_found = len(tasks)

        for task in tasks:
            user = self._db.get(User, task.user_id)
            if not user:
                stats.failed += 1
                stats.errors.append(f"task {task.display_number}: user missing")
                continue

            chat_id = self._chat_id_for_user(user)
            body = self._format_reminder(task)
            outbound = OutboundMessage(
                channel="whatsapp",
                recipient=chat_id,
                message_body=body,
                status="pending",
            )
            self._db.add(outbound)
            self._db.flush()

            try:
                result = await self._waha.send_text(chat_id, body)
                outbound.status = "sent"
                outbound.sent_at = datetime.now(UTC)
                outbound.provider_message_id = str(result.get("id", "") or "") or None
                task.remind_at = None
                self._db.add(
                    TaskEvent(
                        task_id=task.id,
                        event_type="reminder_sent",
                        payload={"chat_id": chat_id, "title": task.title},
                    )
                )
                stats.sent += 1
                self._db.commit()
            except Exception as exc:
                outbound.status = "error"
                outbound.error = str(exc)
                stats.failed += 1
                stats.errors.append(f"task {task.display_number}: {exc}")
                logger.exception("Reminder send failed for T%s", task.display_number)
                self._db.commit()

        return stats

    def _chat_id_for_user(self, user: User) -> str:
        phone = user.phone_number.lstrip("+")
        return f"{phone}@c.us"

    def _format_reminder(self, task: Task) -> str:
        return f"⏰ Reminder: {task.title}"
