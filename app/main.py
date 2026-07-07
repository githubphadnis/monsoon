"""monsoon FastAPI application."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.webhooks import router as webhooks_router
from app.config import get_settings
from app.db import init_db
from app.integrations.ollama.client import OllamaClient
from app.integrations.whatsapp.waha_client import WahaClient
from app.integrations.whatsapp.webhook_setup import ensure_waha_webhook

settings = get_settings()
logging.basicConfig(level=getattr(logging, settings.app_log_level.upper(), logging.INFO))
logger = logging.getLogger("monsoon")


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Initialising database schema")
    init_db()
    await ensure_waha_webhook(settings)
    yield


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
