"""Background sync loops for Gmail, WhatsApp backfill, WorkFlowy, and reminders."""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from datetime import UTC, datetime

from sqlalchemy import select

from app.config import Settings
from app.db import SessionLocal
from app.models import SyncState, User
from app.services.ephemeral_cleanup import EphemeralCleanupService
from app.services.gmail_sync import GmailSyncService
from app.services.reminder_service import ReminderService
from app.services.wa_backfill import WaBackfillService
from app.services.workflowy_mirror import WorkFlowyMirrorService

logger = logging.getLogger("monsoon.background")

GMAIL_STATUS_KEY = "scheduler:gmail"
WA_STATUS_KEY = "scheduler:wa"
WORKFLOWY_STATUS_KEY = "scheduler:workflowy"
REMINDER_STATUS_KEY = "scheduler:reminders"
EPHEMERAL_STATUS_KEY = "scheduler:ephemeral"


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
        for key in (
            GMAIL_STATUS_KEY,
            WA_STATUS_KEY,
            WORKFLOWY_STATUS_KEY,
            REMINDER_STATUS_KEY,
            EPHEMERAL_STATUS_KEY,
        ):
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
        logger.info(
            "Background Gmail batch: inserted=%s skipped=%s",
            stats.get("messages_inserted"),
            stats.get("messages_skipped"),
        )
    except Exception as exc:
        err = str(exc)
        if "invalid_grant" in err or "Token has been expired or revoked" in err:
            logger.warning(
                "Gmail sync paused — refresh token expired/revoked. "
                "Re-run infra/scripts/gmail_oauth_setup.py and update "
                "GMAIL_REFRESH_TOKEN in Portainer. WhatsApp capture still works."
            )
            _set_status(GMAIL_STATUS_KEY, status="auth_error", error=err[:300])
            return
        logger.exception("Background Gmail sync failed")
        _set_status(GMAIL_STATUS_KEY, status="error", error=err[:500])


async def _run_wa_batch(settings: Settings) -> None:
    from app.services.waha_routing import all_waha_sessions

    _set_status(WA_STATUS_KEY, status="running")
    try:
        sessions = all_waha_sessions(settings)
        per_session_cap = max(1, settings.monsoon_wa_sync_batch_chats)
        chats_synced = chats_updated = messages_inserted = messages_skipped = 0
        contacts_upserted = entities_inserted = 0
        errors: list[str] = []
        for session_name in sessions:
            with SessionLocal() as db:
                stats = await WaBackfillService(db, settings, session=session_name).run(
                    full=False,
                    max_chats=per_session_cap,
                )
            chats_synced += stats.chats_synced
            chats_updated += stats.chats_updated
            messages_inserted += stats.messages_inserted
            messages_skipped += stats.messages_skipped
            contacts_upserted += stats.contacts_upserted
            entities_inserted += stats.entities_inserted
            errors.extend(f"{session_name}: {e}" for e in stats.errors)
        _set_status(
            WA_STATUS_KEY,
            status="ok",
            sessions=sessions,
            chats_synced=chats_synced,
            chats_updated=chats_updated,
            messages_inserted=messages_inserted,
            messages_skipped=messages_skipped,
            contacts_upserted=contacts_upserted,
            entities_inserted=entities_inserted,
            errors=errors[:20],
        )
        logger.info(
            "Background WA batch: sessions=%s chats=%s msgs=%s",
            sessions,
            chats_synced + chats_updated,
            messages_inserted,
        )
    except Exception as exc:
        logger.exception("Background WA sync failed")
        _set_status(WA_STATUS_KEY, status="error", error=str(exc))


async def _run_workflowy_sync(settings: Settings) -> None:
    if not settings.workflowy_active:
        _set_status(WORKFLOWY_STATUS_KEY, status="skipped", reason="not_configured")
        return

    def _users() -> list[User]:
        with SessionLocal() as db:
            return list(db.scalars(select(User)))

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


async def _run_reminders(settings: Settings) -> None:
    _set_status(REMINDER_STATUS_KEY, status="running")
    try:
        with SessionLocal() as db:
            stats = await ReminderService(db, settings).send_due()
        _set_status(
            REMINDER_STATUS_KEY,
            status="ok",
            due_found=stats.due_found,
            sent=stats.sent,
            failed=stats.failed,
            errors=list(stats.errors),
        )
        if stats.sent or stats.failed:
            logger.info(
                "Reminders: due=%s sent=%s failed=%s",
                stats.due_found,
                stats.sent,
                stats.failed,
            )
    except Exception as exc:
        logger.exception("Background reminders failed")
        _set_status(REMINDER_STATUS_KEY, status="error", error=str(exc))


async def _run_ephemeral(settings: Settings) -> None:
    if settings.monsoon_ephemeral_seconds <= 0:
        _set_status(EPHEMERAL_STATUS_KEY, status="skipped", reason="disabled")
        return
    _set_status(EPHEMERAL_STATUS_KEY, status="running")
    try:
        with SessionLocal() as db:
            stats = await EphemeralCleanupService(db, settings).run()
        _set_status(
            EPHEMERAL_STATUS_KEY,
            status="ok",
            outbound_deleted=stats.outbound_deleted,
            outbound_failed=stats.outbound_failed,
            inbound_deleted=stats.inbound_deleted,
            inbound_failed=stats.inbound_failed,
            errors=list(stats.errors)[:5],
        )
        if stats.outbound_deleted or stats.inbound_deleted or stats.outbound_failed:
            logger.info(
                "Ephemeral: out_del=%s out_fail=%s in_del=%s in_fail=%s",
                stats.outbound_deleted,
                stats.outbound_failed,
                stats.inbound_deleted,
                stats.inbound_failed,
            )
    except Exception as exc:
        logger.exception("Background ephemeral cleanup failed")
        _set_status(EPHEMERAL_STATUS_KEY, status="error", error=str(exc))


async def _loop(name: str, interval_minutes: int, runner) -> None:
    # Allow sub-minute for reminders (interval expressed in minutes, fractional OK later)
    seconds = max(30, int(interval_minutes * 60))
    # Run immediately once, then sleep — catch-up starts as soon as container is up.
    while True:
        try:
            await runner()
        except Exception:
            logger.exception("Background loop %s crashed; will retry", name)
        logger.debug("Background loop %s sleeping for %ss", name, seconds)
        await asyncio.sleep(seconds)


async def _loop_seconds(name: str, interval_seconds: int, runner) -> None:
    seconds = max(15, int(interval_seconds))
    while True:
        try:
            await runner()
        except Exception:
            logger.exception("Background loop %s crashed; will retry", name)
        await asyncio.sleep(seconds)


def start_background_jobs(settings: Settings) -> list[asyncio.Task]:
    if not settings.monsoon_scheduler_enabled:
        logger.info("Background scheduler disabled by config")
        return []

    logger.info(
        "Starting background jobs: gmail=%sm/%spages wa=%sm/%schats reminders=%sm ephemeral=%ss",
        settings.monsoon_gmail_sync_interval_minutes,
        settings.monsoon_gmail_sync_batch_pages,
        settings.monsoon_wa_sync_interval_minutes,
        settings.monsoon_wa_sync_batch_chats,
        settings.monsoon_reminder_interval_minutes,
        settings.monsoon_ephemeral_seconds,
    )
    tasks = [
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
        asyncio.create_task(
            _loop(
                "reminders",
                settings.monsoon_reminder_interval_minutes,
                lambda: _run_reminders(settings),
            )
        ),
    ]
    if settings.monsoon_ephemeral_seconds > 0:
        tasks.append(
            asyncio.create_task(
                _loop_seconds(
                    "ephemeral",
                    settings.monsoon_ephemeral_interval_seconds,
                    lambda: _run_ephemeral(settings),
                )
            )
        )
    return tasks


async def stop_background_jobs(tasks: list[asyncio.Task]) -> None:
    for task in tasks:
        task.cancel()
    for task in tasks:
        with suppress(asyncio.CancelledError):
            await task
