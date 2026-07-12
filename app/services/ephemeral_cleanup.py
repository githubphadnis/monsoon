"""Ephemeral WhatsApp cleanup — delete monsoon replies (and optional commands) after TTL."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.integrations.whatsapp.waha_client import WahaClient
from app.models import InboundMessage, OutboundMessage
from app.services.waha_routing import session_for_chat_id

logger = logging.getLogger("monsoon.ephemeral")


def extract_waha_message_id(result: dict | None) -> str | None:
    """Normalise WAHA sendText / webhook id shapes to a delete-able message id."""
    if not result:
        return None
    raw = result.get("id")
    if isinstance(raw, dict):
        raw = raw.get("_serialized") or raw.get("id") or raw.get("messageId")
    if raw is None and isinstance(result.get("key"), dict):
        key = result["key"]
        raw = key.get("_serialized") or key.get("id")
    text = str(raw or "").strip()
    return text or None


@dataclass
class EphemeralStats:
    outbound_due: int = 0
    outbound_deleted: int = 0
    outbound_failed: int = 0
    inbound_due: int = 0
    inbound_deleted: int = 0
    inbound_failed: int = 0
    errors: list[str] = field(default_factory=list)


class EphemeralCleanupService:
    def __init__(self, db: Session, settings: Settings, waha: WahaClient | None = None) -> None:
        self._db = db
        self._settings = settings
        self._waha = waha or WahaClient(settings)

    @property
    def enabled(self) -> bool:
        return self._settings.monsoon_ephemeral_seconds > 0

    async def run(self) -> EphemeralStats:
        stats = EphemeralStats()
        if not self.enabled:
            return stats

        ttl = timedelta(seconds=self._settings.monsoon_ephemeral_seconds)
        cutoff = datetime.now(UTC) - ttl

        await self._purge_outbound(cutoff, stats)
        if self._settings.monsoon_ephemeral_delete_commands:
            await self._purge_inbound(cutoff, stats)
        self._db.commit()
        return stats

    async def _purge_outbound(self, cutoff: datetime, stats: EphemeralStats) -> None:
        rows = list(
            self._db.scalars(
                select(OutboundMessage)
                .where(
                    OutboundMessage.status == "sent",
                    OutboundMessage.sent_at.is_not(None),
                    OutboundMessage.sent_at <= cutoff,
                    OutboundMessage.provider_message_id.is_not(None),
                )
                .order_by(OutboundMessage.sent_at.asc())
                .limit(40)
            )
        )
        stats.outbound_due = len(rows)
        for row in rows:
            msg_id = (row.provider_message_id or "").strip()
            if not msg_id:
                row.status = "delete_skipped"
                continue
            try:
                session = row.waha_session or session_for_chat_id(
                    self._settings, row.recipient
                )
                await self._waha.delete_message(
                    row.recipient, msg_id, session=session
                )
                row.status = "deleted"
                stats.outbound_deleted += 1
            except Exception as exc:
                row.status = "delete_failed"
                row.error = str(exc)[:500]
                stats.outbound_failed += 1
                stats.errors.append(f"outbound {row.id}: {exc}")
                logger.warning(
                    "Ephemeral delete failed chat=%s msg=%s: %s",
                    row.recipient,
                    msg_id,
                    exc,
                )

    async def _purge_inbound(self, cutoff: datetime, stats: EphemeralStats) -> None:
        """Best-effort delete of command messages.

        Self-chat (fromMe) commands revoke for everyone.
        Peer commands usually only clear on the monsoon device.
        """
        rows = list(
            self._db.scalars(
                select(InboundMessage)
                .where(
                    InboundMessage.status == "processed",
                    InboundMessage.received_at <= cutoff,
                    InboundMessage.source == "whatsapp",
                )
                .order_by(InboundMessage.received_at.asc())
                .limit(40)
            )
        )
        stats.inbound_due = len(rows)
        for row in rows:
            msg_id = (row.source_message_id or "").strip()
            if not msg_id:
                row.status = "delete_skipped"
                continue
            try:
                session = session_for_chat_id(self._settings, row.chat_id)
                # Prefer session stamped on related outbound echo if present in raw payload
                raw = row.raw_payload if isinstance(row.raw_payload, dict) else {}
                inbound_session = raw.get("session")
                if isinstance(inbound_session, str) and inbound_session.strip():
                    session = inbound_session.strip()
                await self._waha.delete_message(row.chat_id, msg_id, session=session)
                row.status = "deleted"
                stats.inbound_deleted += 1
            except Exception as exc:
                row.status = "delete_failed"
                row.error = str(exc)[:500]
                stats.inbound_failed += 1
                stats.errors.append(f"inbound {row.id}: {exc}")
                logger.warning(
                    "Ephemeral inbound delete failed chat=%s msg=%s: %s",
                    row.chat_id,
                    msg_id,
                    exc,
                )
