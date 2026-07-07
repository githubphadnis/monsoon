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
    yield
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


@app.get("/health/wa-index")
def health_wa_index() -> dict[str, object]:
    from app.db import SessionLocal
    from app.services.wa_backfill import index_counts

    with SessionLocal() as db:
        counts = index_counts(db, settings.waha_session)
    return {"status": "ok", "session": settings.waha_session, **counts}


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
        "workflowy_configured": bool(settings.workflowy_api_key),
    }


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "monsoon", "docs": "/docs", "webhook": settings.waha_webhook_path}
