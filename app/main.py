"""monsoon FastAPI application — health stubs; capture loop in Phase 1."""

import logging

from fastapi import FastAPI

from app.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("monsoon")

settings = get_settings()

app = FastAPI(
    title="monsoon",
    description="Personal Capture & Reminder — WorkFlowy + WhatsApp",
    version="0.1.0",
)


@app.get("/health/live")
def health_live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def health_ready() -> dict[str, str | bool]:
    # Phase 1+: probe Postgres and WAHA here.
    return {
        "status": "ok",
        "database": bool(settings.database_url),
        "workflowy_configured": bool(settings.workflowy_api_key),
        "waha_configured": bool(settings.waha_api_key),
    }


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "monsoon", "docs": "/docs"}
