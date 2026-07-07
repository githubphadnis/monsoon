"""Backfill WhatsApp chat history from WAHA into Postgres index."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.integrations.whatsapp.wa_index import chat_fields, message_fields, phone_from_jid
from app.integrations.whatsapp.waha_client import WahaClient
from app.models import ExtractedEntity, WaChat, WaContact, WaMessage
from app.services.wa_entity_extract import extract_entities_from_text

logger = logging.getLogger("monsoon.wa_backfill")


@dataclass
class BackfillStats:
    chats_synced: int = 0
    chats_updated: int = 0
    messages_inserted: int = 0
    messages_skipped: int = 0
    contacts_upserted: int = 0
    entities_inserted: int = 0
    errors: list[str] = field(default_factory=list)


class WaBackfillService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self._db = db
        self._settings = settings
        self._waha = WahaClient(settings)
        self._session = settings.waha_session

    async def run(
        self,
        *,
        full: bool = True,
        max_chats: int | None = None,
        chat_id: str | None = None,
    ) -> BackfillStats:
        stats = BackfillStats()
        if chat_id:
            chat = await self._upsert_chat({"id": chat_id}, stats)
            if chat:
                await self._sync_chat_messages(chat, stats, reset_offset=full)
            self._db.commit()
            return stats

        offset = 0
        page_size = self._settings.monsoon_wa_backfill_chat_page_size
        processed = 0

        while True:
            if max_chats is not None and processed >= max_chats:
                break
            try:
                chats = await self._waha.list_chats(limit=page_size, offset=offset)
            except Exception as exc:
                stats.errors.append(f"list_chats offset={offset}: {exc}")
                logger.exception("list_chats failed")
                break

            if not chats:
                break

            for raw_chat in chats:
                if max_chats is not None and processed >= max_chats:
                    break
                chat = await self._upsert_chat(raw_chat, stats)
                if chat:
                    await self._sync_chat_messages(chat, stats, reset_offset=full and chat.backfill_offset == 0)
                processed += 1
                await self._delay()

            if len(chats) < page_size:
                break
            offset += page_size
            await self._delay()

        self._db.commit()
        return stats

    async def _upsert_chat(self, raw: dict, stats: BackfillStats) -> WaChat | None:
        fields = chat_fields(raw)
        chat_id = fields["chat_id"]
        if not chat_id:
            return None

        chat = self._db.scalar(
            select(WaChat).where(WaChat.session == self._session, WaChat.chat_id == chat_id)
        )
        if chat:
            chat.name = fields["name"] or chat.name
            chat.chat_type = fields["chat_type"]
            if fields["last_message_at"]:
                chat.last_message_at = fields["last_message_at"]
            chat.raw = raw
            stats.chats_updated += 1
        else:
            chat = WaChat(
                session=self._session,
                chat_id=chat_id,
                name=fields["name"],
                chat_type=fields["chat_type"],
                last_message_at=fields["last_message_at"],
                raw=raw,
            )
            self._db.add(chat)
            stats.chats_synced += 1

        self._db.flush()
        self._upsert_contact(
            jid=chat_id,
            display_name=fields["name"],
            contact_type=fields["chat_type"],
            raw=raw,
            stats=stats,
        )
        return chat

    async def _sync_chat_messages(
        self,
        chat: WaChat,
        stats: BackfillStats,
        *,
        reset_offset: bool,
    ) -> None:
        if reset_offset:
            chat.backfill_offset = 0
            chat.backfill_complete = False

        page_size = self._settings.monsoon_wa_backfill_message_page_size
        offset = chat.backfill_offset

        while True:
            try:
                messages = await self._waha.get_chat_messages(
                    chat.chat_id, limit=page_size, offset=offset
                )
            except Exception as exc:
                stats.errors.append(f"messages {chat.chat_id} offset={offset}: {exc}")
                logger.exception("get_chat_messages failed for %s", chat.chat_id)
                break

            if not messages:
                chat.backfill_complete = True
                break

            inserted = 0
            for raw_msg in messages:
                if self._index_message(chat, raw_msg, stats):
                    inserted += 1

            offset += page_size
            chat.backfill_offset = offset
            self._db.flush()

            if len(messages) < page_size:
                chat.backfill_complete = True
                break

            await self._delay()

        chat.message_count = self._db.scalar(
            select(func.count()).select_from(WaMessage).where(WaMessage.chat_uuid == chat.id)
        ) or 0

    def _index_message(self, chat: WaChat, raw: dict, stats: BackfillStats) -> bool:
        fields = message_fields(raw)
        msg_id = fields["waha_message_id"]
        if not msg_id:
            stats.messages_skipped += 1
            return False

        exists = self._db.scalar(
            select(WaMessage.id).where(
                WaMessage.session == self._session,
                WaMessage.waha_message_id == msg_id,
            )
        )
        if exists:
            stats.messages_skipped += 1
            return False

        row = WaMessage(
            session=self._session,
            chat_uuid=chat.id,
            chat_id=chat.chat_id,
            waha_message_id=msg_id,
            from_id=fields["from_id"],
            from_me=fields["from_me"],
            body=fields["body"],
            has_media=fields["has_media"],
            message_ts=fields["message_ts"],
            message_ts_raw=fields["message_ts_raw"],
            raw=raw,
        )
        self._db.add(row)
        stats.messages_inserted += 1

        if fields["from_id"]:
            self._upsert_contact(
                jid=fields["from_id"],
                display_name=None,
                contact_type="participant",
                raw={"from": fields["from_id"]},
                stats=stats,
            )

        if self._settings.monsoon_wa_backfill_extract_entities and fields["body"]:
            self._extract_entities(msg_id, fields["body"], stats)

        return True

    def _upsert_contact(
        self,
        *,
        jid: str,
        display_name: str | None,
        contact_type: str,
        raw: dict,
        stats: BackfillStats,
    ) -> None:
        if not jid:
            return

        phone = phone_from_jid(jid)
        contact = self._db.scalar(
            select(WaContact).where(WaContact.session == self._session, WaContact.jid == jid)
        )
        if contact:
            if display_name and not contact.display_name:
                contact.display_name = display_name
            if phone and not contact.phone:
                contact.phone = phone
            contact.last_seen_at = datetime.now(UTC)
            contact.raw = raw
        else:
            contact = WaContact(
                session=self._session,
                jid=jid,
                phone=phone,
                display_name=display_name,
                contact_type=contact_type,
                source="chat_derived",
                raw=raw,
            )
            self._db.add(contact)
            stats.contacts_upserted += 1

    def _extract_entities(self, msg_id: str, body: str, stats: BackfillStats) -> None:
        for entity_type, value in extract_entities_from_text(body):
            self._db.add(
                ExtractedEntity(
                    source_type="wa_message",
                    source_id=msg_id,
                    entity_type=entity_type,
                    value=value,
                    meta=None,
                )
            )
            stats.entities_inserted += 1

    async def _delay(self) -> None:
        ms = self._settings.monsoon_wa_backfill_request_delay_ms
        if ms > 0:
            await asyncio.sleep(ms / 1000.0)


def index_counts(db: Session, session: str) -> dict[str, int]:
    return {
        "chats": db.scalar(select(func.count()).select_from(WaChat).where(WaChat.session == session))
        or 0,
        "messages": db.scalar(
            select(func.count()).select_from(WaMessage).where(WaMessage.session == session)
        )
        or 0,
        "contacts": db.scalar(
            select(func.count()).select_from(WaContact).where(WaContact.session == session)
        )
        or 0,
        "entities": db.scalar(select(func.count()).select_from(ExtractedEntity)) or 0,
        "chats_complete": db.scalar(
            select(func.count())
            .select_from(WaChat)
            .where(WaChat.session == session, WaChat.backfill_complete.is_(True))
        )
        or 0,
    }
