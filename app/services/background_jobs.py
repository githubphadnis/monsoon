"""Background sync loops for Gmail, WhatsApp backfill, and WorkFlowy reconciliation."""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from datetime import UTC, datetime

from app.config import Settings
from app.db import SessionLocal
from app.models import SyncState
from app.services.gmail_sync import GmailSyncService
from app.services.wa_backfill import WaBackfillService
from app.services.workflowy_mirror import WorkFlowyMirrorService

logger = logging.getLogger("monsoon.background")

GMAIL_STATUS_KEY = "scheduler:gmail"
WA_STATUS_KEY = "scheduler:wa"
WORKFLOWY_STATUS_KEY = "scheduler:workflowy"


def _set_status(key: str, **fields: object) -> None:
    with SessionLocal() as db:
        row = db.get(SyncState, key)
        payload = {"updated": datetime.now(UTC).isoformat(), **fields}
        if row:
            row.value = payload
        else:
            db.add(SyncState(key=key, value=payload))
        db.commit()


def scheduler_status() -> dict[str, object]:
    with SessionLocal() as db:
        result: dict[str, object] = {}
        for key in (GMAIL_STATUS_KEY, WA_STATUS_KEY, WORKFLOWY_STATUS_KEY):
            row = db.get(SyncState, key)
            result[key.split(":")[1]] = row.value if row and row.value else None
        return result


async def _run_gmail_batch(settings: Settings) -> None:
    if not settings.gmail_configured:
        _set_status(GMAIL_STATUS_KEY, status="skipped", reason="not_configured")
        return

    def _sync() -> dict[str, object]:
        with SessionLocal() as db:
            stats = GmailSyncService(db, settings).run(
                full=False,
                max_pages=settings.monsoon_gmail_sync_batch_pages,
            )
            return {
                "threads_upserted": stats.threads_upserted,
                "messages_inserted": stats.messages_inserted,
                "messages_skipped": stats.messages_skipped,
                "participants_upserted": stats.participants_upserted,
                "entities_inserted": stats.entities_inserted,
                "errors": list(stats.errors),
            }

    _set_status(GMAIL_STATUS_KEY, status="running")
    try:
        stats = await asyncio.to_thread(_sync)
        _set_status(GMAIL_STATUS_KEY, status="ok", **stats)
    except Exception as exc:
        logger.exception("Background Gmail sync failed")
        _set_status(GMAIL_STATUS_KEY, status="error", error=str(exc))


async def _run_wa_batch(settings: Settings) -> None:
    _set_status(WA_STATUS_KEY, status="running")
    try:
        with SessionLocal() as db:
            stats = await WaBackfillService(db, settings).run(
                full=False,
                max_chats=settings.monsoon_wa_sync_batch_chats,
            )
        _set_status(
            WA_STATUS_KEY,
            status="ok",
            chats_synced=stats.chats_synced,
            chats_updated=stats.chats_updated,
            messages_inserted=stats.messages_inserted,
            messages_skipped=stats.messages_skipped,
            contacts_upserted=stats.contacts_upserted,
            entities_inserted=stats.entities_inserted,
            errors=list(stats.errors),
        )
    except Exception as exc:
        logger.exception("Background WA sync failed")
        _set_status(WA_STATUS_KEY, status="error", error=str(exc))


async def _run_workflowy_sync(settings: Settings) -> None:
    if not settings.workflowy_active:
        _set_status(WORKFLOWY_STATUS_KEY, status="skipped", reason="not_configured")
        return

    def _users() -> list[object]:
        from app.models import User
        from sqlalchemy import select

        with SessionLocal() as db:
            return list(db.scalars(select(User).where(User.workflowy_root_node_id.is_not(None))))

    users = await asyncio.to_thread(_users)
    synced = 0
    _set_status(WORKFLOWY_STATUS_KEY, status="running", users=len(users))
    try:
        for user in users:
            with SessionLocal() as db:
                service = WorkFlowyMirrorService(db, settings)
                synced += await service.sync_user_context(user.id)
                db.commit()
        _set_status(WORKFLOWY_STATUS_KEY, status="ok", tasks_synced=synced, users=len(users))
    except Exception as exc:
        logger.exception("Background WorkFlowy sync failed")
        _set_status(WORKFLOWY_STATUS_KEY, status="error", error=str(exc), tasks_synced=synced)


async def _loop(name: str, interval_minutes: int, runner) -> None:
    seconds = max(60, interval_minutes * 60)
    while True:
        await runner()
        logger.debug("Background loop %s sleeping for %ss", name, seconds)
        await asyncio.sleep(seconds)


def start_background_jobs(settings: Settings) -> list[asyncio.Task]:
    if not settings.monsoon_scheduler_enabled:
        logger.info("Background scheduler disabled by config")
        return []

    return [
        asyncio.create_task(
            _loop("gmail", settings.monsoon_gmail_sync_interval_minutes, lambda: _run_gmail_batch(settings))
        ),
        asyncio.create_task(
            _loop("wa", settings.monsoon_wa_sync_interval_minutes, lambda: _run_wa_batch(settings))
        ),
        asyncio.create_task(
            _loop(
                "workflowy",
                settings.monsoon_workflowy_sync_interval_minutes,
                lambda: _run_workflowy_sync(settings),
            )
        ),
    ]


async def stop_background_jobs(tasks: list[asyncio.Task]) -> None:
    for task in tasks:
        task.cancel()
    for task in tasks:
        with suppress(asyncio.CancelledError):
            await task
