"""Configure WAHA session webhook to reach this app (idempotent)."""

from __future__ import annotations

import asyncio
import logging

import httpx

from app.config import Settings

logger = logging.getLogger("monsoon.waha.webhook_setup")


def configure_waha_webhook(settings: Settings) -> bool:
    """Point WAHA at monsoon. Returns True when session webhook is configured."""
    if not settings.monsoon_auto_webhook:
        return False

    target_url = settings.monsoon_webhook_target_url
    if not target_url:
        target_url = f"http://monsoon-app:8080{settings.waha_webhook_path}"

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if settings.waha_api_key:
        headers["X-Api-Key"] = settings.waha_api_key

    webhook: dict = {
        "url": target_url,
        "events": ["message", "message.any"],
    }
    if settings.waha_api_key:
        webhook["customHeaders"] = [{"name": "X-Api-Key", "value": settings.waha_api_key}]

    payload = {
        "name": settings.waha_session,
        "config": {"webhooks": [webhook]},
    }

    base = settings.waha_base_url.rstrip("/")
    session = settings.waha_session

    with httpx.Client(timeout=30.0) as client:
        try:
            response = client.get(f"{base}/api/sessions/{session}", headers=headers)
            if response.status_code == 404:
                logger.warning(
                    "WAHA session %r not found yet — pair WhatsApp in dashboard, then redeploy app",
                    session,
                )
                return False
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("WAHA not ready for webhook setup: %s", exc)
            return False

        response = client.put(
            f"{base}/api/sessions/{session}",
            headers=headers,
            json={"config": payload["config"]},
        )
        try:
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("WAHA webhook configure failed: %s", exc)
            return False

    logger.info("WAHA webhook configured: %s → %s", session, target_url)
    return True


async def ensure_waha_webhook(settings: Settings, *, attempts: int = 5) -> None:
    """Retry webhook setup until WAHA session exists (e.g. after Portainer redeploy)."""
    if not settings.monsoon_auto_webhook:
        return

    for attempt in range(1, attempts + 1):
        if await asyncio.to_thread(configure_waha_webhook, settings):
            return
        if attempt < attempts:
            await asyncio.sleep(5 * attempt)

    logger.warning(
        "Could not configure WAHA webhook after %s attempts — check session %r is WORKING",
        attempts,
        settings.waha_session,
    )
