"""Scheduled morning daily summary (tasks + person WA + Gmail for recipients)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.config import Settings
from app.integrations.whatsapp.waha_client import WahaClient
from app.models import OutboundMessage, SyncState
from app.services.capture_service import CaptureService
from app.services.ephemeral_cleanup import extract_waha_message_id, serialize_waha_message_id
from app.services.users import get_or_create_user
from app.services.waha_routing import session_for_phone

logger = logging.getLogger("monsoon.daily_digest")

LAST_SENT_KEY = "daily_digest:last_sent_date"


@dataclass
class DailyDigestStats:
    due: bool = False
    sent: int = 0
    failed: int = 0
    skipped: str = ""
    errors: list[str] = field(default_factory=list)


class DailyDigestService:
    def __init__(
        self, db: Session, settings: Settings, waha: WahaClient | None = None
    ) -> None:
        self._db = db
        self._settings = settings
        self._waha = waha or WahaClient(settings)

    def should_send_now(self, now: datetime | None = None) -> bool:
        if not self._settings.monsoon_daily_digest_enabled:
            return False
        tz = ZoneInfo(self._settings.app_timezone)
        local = (now or datetime.now(UTC)).astimezone(tz)
        target = local.replace(
            hour=self._settings.monsoon_daily_digest_hour,
            minute=self._settings.monsoon_daily_digest_minute,
            second=0,
            microsecond=0,
        )
        if local < target:
            return False
        today = local.date().isoformat()
        last = self._last_sent_date()
        return last != today

    async def run_if_due(self, now: datetime | None = None) -> DailyDigestStats:
        stats = DailyDigestStats()
        if not self._settings.monsoon_daily_digest_enabled:
            stats.skipped = "disabled"
            return stats
        if not self.should_send_now(now):
            stats.skipped = "not_due"
            return stats

        stats.due = True
        phones = self._settings.daily_digest_recipient_phones()
        if not phones:
            stats.skipped = "no_recipients"
            logger.warning("Daily digest due but no recipient phones configured")
            return stats

        capture = CaptureService(self._db, self._settings)
        for phone in phones:
            chat_id = f"{phone.lstrip('+')}@c.us"
            user = get_or_create_user(self._db, phone, self._settings)
            try:
                body = await capture.compose_digest_text(user, chat_id=chat_id)
                text = f"*Daily summary*\n{body}".strip()
                session = session_for_phone(self._settings, phone)
                await self._send(chat_id, text, session=session)
                stats.sent += 1
            except Exception as exc:
                stats.failed += 1
                stats.errors.append(f"{phone}: {exc}")
                logger.exception("Daily digest failed for %s", phone)

        tz = ZoneInfo(self._settings.app_timezone)
        local = (now or datetime.now(UTC)).astimezone(tz)
        self._set_last_sent_date(local.date().isoformat())
        self._db.commit()
        return stats

    async def _send(self, chat_id: str, text: str, *, session: str) -> None:
        outbound = OutboundMessage(
            channel="whatsapp",
            recipient=chat_id,
            message_body=text,
            status="pending",
            waha_session=session,
        )
        self._db.add(outbound)
        self._db.flush()
        try:
            result = await self._waha.send_text(chat_id, text, session=session)
            outbound.status = "sent"
            outbound.sent_at = datetime.now(UTC)
            raw_id = extract_waha_message_id(result)
            outbound.provider_message_id = (
                serialize_waha_message_id(chat_id, raw_id, from_me=True)
                if raw_id
                else None
            )
        except Exception as exc:
            outbound.status = "error"
            outbound.error = str(exc)[:500]
            raise

    def _last_sent_date(self) -> str | None:
        row = self._db.get(SyncState, LAST_SENT_KEY)
        if not row or not row.value:
            return None
        return str(row.value.get("date") or "") or None

    def _set_last_sent_date(self, date_iso: str) -> None:
        payload = {"date": date_iso, "updated": datetime.now(UTC).isoformat()}
        row = self._db.get(SyncState, LAST_SENT_KEY)
        if row:
            row.value = payload
        else:
            self._db.add(SyncState(key=LAST_SENT_KEY, value=payload))
        self._db.flush()
