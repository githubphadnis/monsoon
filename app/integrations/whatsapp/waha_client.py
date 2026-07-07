"""WAHA HTTP client for outbound WhatsApp messages."""

import logging

import httpx

from app.config import Settings

logger = logging.getLogger("monsoon.waha")


class WahaClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base = settings.waha_base_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self._settings.waha_api_key:
            headers["X-Api-Key"] = self._settings.waha_api_key
        return headers

    async def send_text(self, chat_id: str, text: str, reply_to: str | None = None) -> dict:
        payload: dict[str, str] = {
            "session": self._settings.waha_session,
            "chatId": chat_id,
            "text": text,
        }
        if reply_to:
            payload["reply_to"] = reply_to

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self._base}/api/sendText",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            logger.info("Sent WhatsApp message to %s", chat_id)
            return data

    async def ping(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self._base}/api/sessions", headers=self._headers())
                return response.status_code < 500
        except httpx.HTTPError:
            return False
