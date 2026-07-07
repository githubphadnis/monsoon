"""WAHA HTTP client for outbound WhatsApp messages."""

import logging
from urllib.parse import quote

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
            if response.is_error:
                logger.error(
                    "WAHA sendText failed status=%s session=%s chatId=%s body=%s",
                    response.status_code,
                    self._settings.waha_session,
                    chat_id,
                    response.text[:500],
                )
            response.raise_for_status()
            data = response.json()
            logger.info("Sent WhatsApp message to %s via session %s", chat_id, self._settings.waha_session)
            return data

    async def ping(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self._base}/api/sessions", headers=self._headers())
                return response.status_code < 500
        except httpx.HTTPError:
            return False

    def _session_base(self) -> str:
        return f"{self._base}/api/{self._settings.waha_session}"

    async def list_chats(self, *, limit: int = 50, offset: int = 0) -> list[dict]:
        params = {
            "limit": limit,
            "offset": offset,
            "sortBy": "messageTimestamp",
            "sortOrder": "desc",
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(
                f"{self._session_base()}/chats",
                headers=self._headers(),
                params=params,
            )
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                return data
            return list(data.get("chats") or data.get("data") or [])

    async def get_chat_messages(
        self,
        chat_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        encoded = quote(chat_id, safe="")
        params = {"limit": limit, "offset": offset, "downloadMedia": "false"}
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(
                f"{self._session_base()}/chats/{encoded}/messages",
                headers=self._headers(),
                params=params,
            )
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                return data
            return list(data.get("messages") or data.get("data") or [])
