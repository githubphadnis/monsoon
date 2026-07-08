"""Sync Gmail into Postgres index."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.integrations.gmail.client import build_gmail_service
from app.integrations.gmail.parse import (
    decode_body,
    header_map,
    parse_address_list,
    parse_date,
    parse_from,
)
from app.models import EmailMessage, EmailParticipant, EmailThread, ExtractedEntity, SyncState
from app.services.wa_entity_extract import extract_entities_from_text

logger = logging.getLogger("monsoon.gmail_sync")

HISTORY_KEY = "gmail:history_id"
PAGE_TOKEN_KEY = "gmail:list_page_token"


@dataclass
class GmailSyncStats:
    threads_upserted: int = 0
    messages_inserted: int = 0
    messages_skipped: int = 0
    participants_upserted: int = 0
    entities_inserted: int = 0
    errors: list[str] = field(default_factory=list)


class GmailSyncService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self._db = db
        self._settings = settings
        self._service = build_gmail_service(settings)

    def run(self, *, full: bool = False, max_pages: int | None = None) -> GmailSyncStats:
        stats = GmailSyncStats()
        if full:
            self._set_sync_value(PAGE_TOKEN_KEY, None)
            self._set_sync_value(HISTORY_KEY, None)

        # Resume incomplete list sync even if a historyId was saved mid-pilot.
        list_in_progress = bool(self._get_sync_value(PAGE_TOKEN_KEY))
        if list_in_progress and not full:
            self._sync_list(stats, max_pages=max_pages or self._settings.gmail_sync_max_pages)
        elif self._get_sync_value(HISTORY_KEY) and not full:
            self._sync_history(stats)
        else:
            self._sync_list(stats, max_pages=max_pages or self._settings.gmail_sync_max_pages)

        # Only advance history cursor when the mailbox list pass is finished.
        if not self._get_sync_value(PAGE_TOKEN_KEY):
            profile = self._service.users().getProfile(
                userId=self._settings.gmail_user_id
            ).execute()
            history_id = profile.get("historyId")
            if history_id:
                self._set_sync_value(HISTORY_KEY, str(history_id))

        self._db.commit()
        return stats

    def _sync_list(self, stats: GmailSyncStats, *, max_pages: int | None) -> None:
        page_token = self._get_sync_value(PAGE_TOKEN_KEY)
        pages = 0
        page_size = self._settings.gmail_sync_page_size

        while True:
            if max_pages is not None and pages >= max_pages:
                self._set_sync_value(PAGE_TOKEN_KEY, page_token)
                break

            params: dict = {
                "userId": self._settings.gmail_user_id,
                "maxResults": page_size,
                # False = All Mail including Archive; Spam/Trash only if enabled.
                "includeSpamTrash": bool(self._settings.gmail_include_spam_trash),
            }
            if page_token:
                params["pageToken"] = page_token
            if self._settings.gmail_sync_label:
                # INBOX only excludes Archive — leave empty for full mailbox index.
                params["labelIds"] = [self._settings.gmail_sync_label]

            try:
                result = self._service.users().messages().list(**params).execute()
            except Exception as exc:
                stats.errors.append(f"messages.list: {exc}")
                logger.exception("Gmail list failed")
                break

            for item in result.get("messages") or []:
                msg_id = item.get("id")
                if msg_id:
                    self._index_message(msg_id, stats, fetch_body=False)

            page_token = result.get("nextPageToken")
            pages += 1
            if not page_token:
                self._set_sync_value(PAGE_TOKEN_KEY, None)
                break
            self._set_sync_value(PAGE_TOKEN_KEY, page_token)

    def _sync_history(self, stats: GmailSyncStats) -> None:
        start_id = self._get_sync_value(HISTORY_KEY)
        if not start_id:
            return

        page_token = None
        while True:
            params: dict = {
                "userId": self._settings.gmail_user_id,
                "startHistoryId": start_id,
            }
            if page_token:
                params["pageToken"] = page_token

            try:
                result = self._service.users().history().list(**params).execute()
            except Exception as exc:
                if "404" in str(exc) or "historyId" in str(exc).lower():
                    logger.warning("Gmail history expired — falling back to list sync")
                    self._set_sync_value(HISTORY_KEY, None)
                    self._sync_list(stats, max_pages=self._settings.gmail_sync_max_pages)
                    return
                stats.errors.append(f"history.list: {exc}")
                logger.exception("Gmail history failed")
                break

            for record in result.get("history") or []:
                for added in record.get("messagesAdded") or []:
                    msg = added.get("message") or {}
                    msg_id = msg.get("id")
                    if msg_id:
                        self._index_message(msg_id, stats, fetch_body=False)

            page_token = result.get("nextPageToken")
            if not page_token:
                break

    def _index_message(self, gmail_message_id: str, stats: GmailSyncStats, *, fetch_body: bool) -> None:
        exists = self._db.scalar(
            select(EmailMessage.id).where(EmailMessage.gmail_message_id == gmail_message_id)
        )
        if exists:
            stats.messages_skipped += 1
            return

        fmt = "full" if fetch_body else "metadata"
        metadata_headers = ["From", "To", "Cc", "Subject", "Date"]
        try:
            raw = (
                self._service.users()
                .messages()
                .get(
                    userId=self._settings.gmail_user_id,
                    id=gmail_message_id,
                    format=fmt,
                    metadataHeaders=metadata_headers,
                )
                .execute()
            )
        except Exception as exc:
            stats.errors.append(f"messages.get {gmail_message_id}: {exc}")
            return

        thread_id = str(raw.get("threadId") or "")
        if not thread_id:
            return

        thread = self._upsert_thread(thread_id, raw, stats)
        payload = raw.get("payload") or {}
        headers = header_map(payload)
        from_email, from_name = parse_from(headers)
        to_addrs = parse_address_list(headers.get("to"))
        cc_addrs = parse_address_list(headers.get("cc"))
        subject = headers.get("subject")
        received_at = parse_date(headers)
        snippet = raw.get("snippet")
        body_text = decode_body(payload) if fetch_body else None

        row = EmailMessage(
            thread_uuid=thread.id,
            gmail_message_id=gmail_message_id,
            gmail_thread_id=thread_id,
            from_email=from_email,
            from_name=from_name,
            to_addrs=to_addrs or None,
            cc_addrs=cc_addrs or None,
            subject=subject,
            snippet=snippet,
            body_text=body_text,
            received_at=received_at,
            label_ids=raw.get("labelIds"),
            raw_headers=headers,
        )
        self._db.add(row)
        stats.messages_inserted += 1

        if from_email:
            self._upsert_participant(from_email, from_name, stats)
        for addr in to_addrs + cc_addrs:
            self._upsert_participant(addr["email"], addr.get("name"), stats)

        text_for_entities = " ".join(filter(None, [subject, snippet, body_text]))
        for entity_type, value in extract_entities_from_text(text_for_entities):
            self._db.add(
                ExtractedEntity(
                    source_type="email_message",
                    source_id=gmail_message_id,
                    entity_type=entity_type,
                    value=value,
                )
            )
            stats.entities_inserted += 1

        if received_at and (not thread.last_message_at or received_at > thread.last_message_at):
            thread.last_message_at = received_at
        if subject and not thread.subject:
            thread.subject = subject
        if snippet:
            thread.snippet = snippet

        thread.message_count = (thread.message_count or 0) + 1
        self._db.flush()

    def _upsert_thread(self, gmail_thread_id: str, raw_msg: dict, stats: GmailSyncStats) -> EmailThread:
        thread = self._db.scalar(
            select(EmailThread).where(EmailThread.gmail_thread_id == gmail_thread_id)
        )
        if thread:
            return thread

        thread = EmailThread(
            gmail_thread_id=gmail_thread_id,
            subject=(header_map(raw_msg.get("payload") or {}).get("subject")),
            snippet=raw_msg.get("snippet"),
            raw={"source": "message_get"},
        )
        self._db.add(thread)
        self._db.flush()
        stats.threads_upserted += 1
        return thread

    def _upsert_participant(
        self, email: str, display_name: str | None, stats: GmailSyncStats
    ) -> None:
        email = email.lower()
        for pending in self._db.new:
            if isinstance(pending, EmailParticipant) and pending.email == email:
                if display_name and not pending.display_name:
                    pending.display_name = display_name
                return
        row = self._db.scalar(select(EmailParticipant).where(EmailParticipant.email == email))
        if row:
            if display_name and not row.display_name:
                row.display_name = display_name
            row.last_seen_at = datetime.now(UTC)
        else:
            self._db.add(EmailParticipant(email=email, display_name=display_name))
            stats.participants_upserted += 1

    def _get_sync_value(self, key: str) -> str | None:
        row = self._db.get(SyncState, key)
        if not row or not row.value:
            return None
        return str(row.value.get("cursor") or row.value.get("value") or "")

    def _set_sync_value(self, key: str, value: str | None) -> None:
        row = self._db.get(SyncState, key)
        payload = {"cursor": value, "updated": datetime.now(UTC).isoformat()}
        if row:
            row.value = payload
        else:
            self._db.add(SyncState(key=key, value=payload))


def gmail_index_counts(db: Session) -> dict[str, int | str | None]:
    from app.models import SyncState

    counts = {
        "threads": db.scalar(select(func.count()).select_from(EmailThread)) or 0,
        "messages": db.scalar(select(func.count()).select_from(EmailMessage)) or 0,
        "participants": db.scalar(select(func.count()).select_from(EmailParticipant)) or 0,
    }
    history_row = db.get(SyncState, HISTORY_KEY)
    if history_row and history_row.value:
        counts["last_history_id"] = history_row.value.get("cursor")
        counts["history_updated"] = history_row.value.get("updated")
    page_row = db.get(SyncState, PAGE_TOKEN_KEY)
    if page_row and page_row.value:
        counts["list_sync_in_progress"] = bool(page_row.value.get("cursor"))
    return counts
