"""Configure WAHA session webhook(s) to reach this app (idempotent)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.config import Settings
from app.services.waha_routing import all_waha_sessions, base_url_for_session

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


def _fetch_session(settings: Settings, session: str) -> dict[str, Any] | None:
    base = base_url_for_session(settings, session)
    headers = _session_headers(settings)

    with httpx.Client(timeout=30.0) as client:
        try:
            response = client.get(f"{base}/api/sessions/{session}", headers=headers)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            logger.warning("WAHA session fetch failed session=%s: %s", session, exc)
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
        "events": ["message.any"],
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


def get_webhook_status_for_session(settings: Settings, session: str) -> dict[str, Any]:
    """Return current vs expected WAHA webhook configuration for one session."""
    target_url = expected_webhook_url(settings)
    session_data = _fetch_session(settings, session)
    if not session_data:
        return {
            "configured": False,
            "session": session,
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
        and "message.any" in set(hook.get("events") or [])
        for hook in webhooks
    )
    store_ok = (not settings.waha_noweb_store_enabled) or _noweb_store_enabled(session_data)
    status = session_data.get("status")

    return {
        "configured": bool(url_ok and events_ok and store_ok),
        "session": session,
        "session_status": status,
        "expected_url": target_url,
        "current_urls": current_urls,
        "events_ok": events_ok,
        "noweb_store_enabled": _noweb_store_enabled(session_data),
        "noweb_store_expected": settings.waha_noweb_store_enabled,
        "detail": None if url_ok and events_ok and store_ok else "webhook_or_store_mismatch",
    }


def get_webhook_status(settings: Settings) -> dict[str, Any]:
    """Aggregate status across all configured WAHA sessions (primary + map)."""
    sessions = all_waha_sessions(settings)
    per = {name: get_webhook_status_for_session(settings, name) for name in sessions}
    primary = per.get(settings.waha_session) or next(iter(per.values()), {})
    all_ok = all(item.get("configured") for item in per.values()) if per else False
    return {
        **primary,
        "configured": all_ok,
        "sessions": sessions,
        "per_session": per,
    }


def configure_waha_webhook_session(settings: Settings, session: str) -> bool:
    """Point one WAHA session at monsoon. Returns True when configured."""
    if not settings.monsoon_auto_webhook:
        return False

    target_url = expected_webhook_url(settings)
    status = get_webhook_status_for_session(settings, session)
    if status["configured"]:
        logger.debug("WAHA webhook already correct for %s", session)
        return True

    if status["session_status"] and status["session_status"] not in {"WORKING", "STARTING"}:
        logger.warning(
            "WAHA session %r status=%r — pair WhatsApp in dashboard first",
            session,
            status["session_status"],
        )

    headers = _session_headers(settings)
    base = base_url_for_session(settings, session)

    with httpx.Client(timeout=30.0) as client:
        try:
            response = client.get(f"{base}/api/sessions/{session}", headers=headers)
            if response.status_code == 404:
                logger.warning(
                    "WAHA session %r not found yet — create/pair in dashboard, then redeploy",
                    session,
                )
                return False
            response.raise_for_status()
            session_data = response.json()
        except httpx.HTTPError as exc:
            logger.warning("WAHA not ready for webhook setup (%s): %s", session, exc)
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
            logger.warning(
                "WAHA webhook configure failed session=%s: %s body=%s",
                session,
                exc,
                body[:500],
            )
            return False

    logger.info(
        "WAHA session configured: %s webhook=%s noweb_store=%s",
        session,
        target_url,
        settings.waha_noweb_store_enabled,
    )
    return True


def configure_waha_webhook(settings: Settings) -> bool:
    """Configure webhooks for every known session. True if all succeed."""
    sessions = all_waha_sessions(settings)
    if not sessions:
        return False
    results = [configure_waha_webhook_session(settings, name) for name in sessions]
    return all(results)


async def ensure_waha_webhook(settings: Settings, *, attempts: int = 12) -> None:
    """Retry webhook setup until WAHA sessions exist (e.g. after Portainer redeploy)."""
    if not settings.monsoon_auto_webhook:
        return

    for attempt in range(1, attempts + 1):
        if await asyncio.to_thread(configure_waha_webhook, settings):
            return
        if attempt < attempts:
            await asyncio.sleep(5 * attempt)

    status = await asyncio.to_thread(get_webhook_status, settings)
    logger.warning(
        "Could not configure WAHA webhook after %s attempts — sessions=%s per=%s",
        attempts,
        status.get("sessions"),
        {
            name: {
                "status": item.get("session_status"),
                "urls": item.get("current_urls"),
            }
            for name, item in (status.get("per_session") or {}).items()
        },
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
                "WAHA webhook mismatch sessions=%s — reconfiguring",
                status.get("sessions"),
            )
            await asyncio.to_thread(configure_waha_webhook, settings)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Webhook reconciler iteration failed")
