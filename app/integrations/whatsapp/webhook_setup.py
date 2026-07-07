"""Configure WAHA session webhook to reach this app (idempotent)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.config import Settings

logger = logging.getLogger("monsoon.waha.webhook_setup")

RECONCILE_INTERVAL_SECONDS = 60


def expected_webhook_url(settings: Settings) -> str:
    if settings.monsoon_webhook_target_url:
        return settings.monsoon_webhook_target_url
    return f"http://127.0.0.1:8080{settings.waha_webhook_path}"


def _session_headers(settings: Settings) -> dict[str, str]:
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if settings.waha_api_key:
        headers["X-Api-Key"] = settings.waha_api_key
    return headers


def _fetch_session(settings: Settings) -> dict[str, Any] | None:
    base = settings.waha_base_url.rstrip("/")
    session = settings.waha_session
    headers = _session_headers(settings)

    with httpx.Client(timeout=30.0) as client:
        try:
            response = client.get(f"{base}/api/sessions/{session}", headers=headers)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            logger.warning("WAHA session fetch failed: %s", exc)
            return None


def _noweb_store_enabled(session_data: dict[str, Any]) -> bool:
    store = (session_data.get("config") or {}).get("noweb", {}).get("store", {})
    return bool(store.get("enabled"))


def _build_session_config(settings: Settings, session_data: dict[str, Any]) -> dict[str, Any]:
    """Merge webhook + NOWEB store settings into existing WAHA session config."""
    config = dict(session_data.get("config") or {})

    target_url = expected_webhook_url(settings)
    webhook: dict[str, Any] = {
        "url": target_url,
        "events": ["message", "message.any"],
    }
    if settings.waha_api_key:
        webhook["customHeaders"] = [{"name": "X-Api-Key", "value": settings.waha_api_key}]
    config["webhooks"] = [webhook]

    if settings.waha_noweb_store_enabled:
        noweb = dict(config.get("noweb") or {})
        store = dict(noweb.get("store") or {})
        store["enabled"] = True
        if settings.waha_noweb_store_full_sync:
            store["fullSync"] = True
        elif "fullSync" not in store:
            store["fullSync"] = False
        noweb["store"] = store
        config["noweb"] = noweb

    return {"config": config}


def get_webhook_status(settings: Settings) -> dict[str, Any]:
    """Return current vs expected WAHA webhook configuration."""
    target_url = expected_webhook_url(settings)
    session_data = _fetch_session(settings)
    if not session_data:
        return {
            "configured": False,
            "session": settings.waha_session,
            "session_status": None,
            "expected_url": target_url,
            "current_urls": [],
            "events_ok": False,
            "noweb_store_enabled": False,
            "noweb_store_expected": settings.waha_noweb_store_enabled,
            "detail": "session_not_found",
        }

    webhooks = session_data.get("config", {}).get("webhooks", [])
    current_urls = [hook.get("url", "") for hook in webhooks if isinstance(hook, dict)]
    url_ok = target_url in current_urls
    events_ok = any(
        isinstance(hook, dict)
        and hook.get("url") == target_url
        and {"message", "message.any"}.issubset(set(hook.get("events") or []))
        for hook in webhooks
    )
    store_ok = (not settings.waha_noweb_store_enabled) or _noweb_store_enabled(session_data)
    status = session_data.get("status")

    return {
        "configured": bool(url_ok and events_ok and store_ok),
        "session": settings.waha_session,
        "session_status": status,
        "expected_url": target_url,
        "current_urls": current_urls,
        "events_ok": events_ok,
        "noweb_store_enabled": _noweb_store_enabled(session_data),
        "noweb_store_expected": settings.waha_noweb_store_enabled,
        "detail": None if url_ok and events_ok and store_ok else "webhook_or_store_mismatch",
    }


def configure_waha_webhook(settings: Settings) -> bool:
    """Point WAHA at monsoon. Returns True when session webhook is configured."""
    if not settings.monsoon_auto_webhook:
        return False

    target_url = expected_webhook_url(settings)
    status = get_webhook_status(settings)
    if status["configured"]:
        logger.debug("WAHA webhook already correct for %s", settings.waha_session)
        return True

    if status["session_status"] and status["session_status"] not in {"WORKING", "STARTING"}:
        logger.warning(
            "WAHA session %r status=%r — pair WhatsApp in dashboard first",
            settings.waha_session,
            status["session_status"],
        )

    headers = _session_headers(settings)
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
            session_data = response.json()
        except httpx.HTTPError as exc:
            logger.warning("WAHA not ready for webhook setup: %s", exc)
            return False

        response = client.put(
            f"{base}/api/sessions/{session}",
            headers=headers,
            json=_build_session_config(settings, session_data),
        )
        try:
            response.raise_for_status()
        except httpx.HTTPError as exc:
            body = response.text if response is not None else ""
            logger.warning("WAHA webhook configure failed: %s body=%s", exc, body[:500])
            return False

    logger.info(
        "WAHA session configured: %s webhook=%s noweb_store=%s",
        session,
        target_url,
        settings.waha_noweb_store_enabled,
    )
    return True


async def ensure_waha_webhook(settings: Settings, *, attempts: int = 12) -> None:
    """Retry webhook setup until WAHA session exists (e.g. after Portainer redeploy)."""
    if not settings.monsoon_auto_webhook:
        return

    for attempt in range(1, attempts + 1):
        if await asyncio.to_thread(configure_waha_webhook, settings):
            return
        if attempt < attempts:
            await asyncio.sleep(5 * attempt)

    status = await asyncio.to_thread(get_webhook_status, settings)
    logger.warning(
        "Could not configure WAHA webhook after %s attempts — status=%s current_urls=%s",
        attempts,
        status.get("session_status"),
        status.get("current_urls"),
    )


async def webhook_reconciler_loop(settings: Settings) -> None:
    """Keep WAHA webhook pointed at localhost (WAHA shares app network namespace)."""
    if not settings.monsoon_auto_webhook:
        return

    while True:
        await asyncio.sleep(RECONCILE_INTERVAL_SECONDS)
        try:
            status = await asyncio.to_thread(get_webhook_status, settings)
            if status["configured"]:
                continue
            logger.info(
                "WAHA webhook mismatch (status=%s urls=%s) — reconfiguring",
                status.get("session_status"),
                status.get("current_urls"),
            )
            await asyncio.to_thread(configure_waha_webhook, settings)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Webhook reconciler iteration failed")
