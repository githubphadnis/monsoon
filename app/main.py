"""monsoon FastAPI application."""

import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from app.api.webhooks import router as webhooks_router
from app.config import get_settings
from app.db import init_db
from app.integrations.ollama.client import OllamaClient
from app.integrations.whatsapp.waha_client import WahaClient
from app.services.background_jobs import scheduler_status, start_background_jobs, stop_background_jobs
from app.integrations.whatsapp.webhook_setup import (
    ensure_waha_webhook,
    get_webhook_status,
    webhook_reconciler_loop,
)

settings = get_settings()
logging.basicConfig(level=getattr(logging, settings.app_log_level.upper(), logging.INFO))
logger = logging.getLogger("monsoon")


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Initialising database schema")
    init_db()
    await ensure_waha_webhook(settings)
    reconciler = asyncio.create_task(webhook_reconciler_loop(settings))
    background_jobs = start_background_jobs(settings)
    yield
    await stop_background_jobs(background_jobs)
    reconciler.cancel()
    with suppress(asyncio.CancelledError):
        await reconciler


app = FastAPI(
    title="monsoon",
    description="Personal Capture & Reminder — WorkFlowy + WhatsApp + Ollama",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(webhooks_router)


@app.get("/health/live")
def health_live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db")
def health_db() -> dict[str, object]:
    from sqlalchemy import text

    from app.db import engine

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as exc:
        logger.exception("Database health check failed")
        return {"status": "error", "detail": str(exc)}


@app.get("/health/webhook")
def health_webhook() -> dict[str, object]:
    status = get_webhook_status(settings)
    return {
        "status": "ok" if status.get("configured") else "misconfigured",
        **status,
        "waha_session_env": settings.waha_session,
        "auto_webhook": settings.monsoon_auto_webhook,
    }


@app.get("/health/gmail-index")
def health_gmail_index() -> dict[str, object]:
    from app.db import SessionLocal
    from app.services.gmail_sync import gmail_index_counts

    with SessionLocal() as db:
        counts = gmail_index_counts(db)
    return {
        "status": "ok" if settings.gmail_configured else "not_configured",
        "configured": settings.gmail_configured,
        "label": settings.gmail_sync_label or "ALL",
        **counts,
    }


@app.get("/health/wa-index")
def health_wa_index() -> dict[str, object]:
    from app.db import SessionLocal
    from app.services.wa_backfill import index_counts

    with SessionLocal() as db:
        counts = index_counts(db, settings.waha_session)
    return {"status": "ok", "session": settings.waha_session, **counts}


@app.get("/health/scheduler")
def health_scheduler() -> dict[str, object]:
    return {
        "status": "ok" if settings.monsoon_scheduler_enabled else "disabled",
        "enabled": settings.monsoon_scheduler_enabled,
        "gmail_interval_minutes": settings.monsoon_gmail_sync_interval_minutes,
        "gmail_batch_pages": settings.monsoon_gmail_sync_batch_pages,
        "gmail_include_spam_trash": settings.gmail_include_spam_trash,
        "gmail_sync_label": settings.gmail_sync_label or "ALL_MAIL",
        "wa_interval_minutes": settings.monsoon_wa_sync_interval_minutes,
        "wa_batch_chats": settings.monsoon_wa_sync_batch_chats,
        "workflowy_interval_minutes": settings.monsoon_workflowy_sync_interval_minutes,
        "reminder_interval_minutes": settings.monsoon_reminder_interval_minutes,
        **scheduler_status(),
    }


@app.get("/health/ready")
async def health_ready() -> dict[str, object]:
    waha = WahaClient(settings)
    ollama = OllamaClient(settings)
    waha_ok = await waha.ping()
    ollama_ok = await ollama.ping()
    ready = bool(settings.database_url) and waha_ok
    return {
        "status": "ok" if ready else "degraded",
        "database_configured": bool(settings.database_url),
        "waha_reachable": waha_ok,
        "ollama_reachable": ollama_ok,
        "gmail_configured": settings.gmail_configured,
        "workflowy_configured": bool(settings.workflowy_api_key),
        "allowed_whatsapp_chat_ids": sorted(settings.allowed_chat_ids_set),
        "shared_whatsapp_chat_ids": sorted(settings.shared_chat_ids_set),
        "chat_allowlist_active": bool(settings.allowed_chat_ids_set),
    }


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "monsoon", "docs": "/docs", "webhook": settings.waha_webhook_path}
