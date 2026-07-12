"""WAHA HTTP client for outbound WhatsApp messages."""

import logging
from urllib.parse import quote

import httpx

from app.config import Settings
from app.services.waha_routing import base_url_for_session

logger = logging.getLogger("monsoon.waha")


class WahaClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self._settings.waha_api_key:
            headers["X-Api-Key"] = self._settings.waha_api_key
        return headers

    def _resolve(self, session: str | None) -> tuple[str, str]:
        name = (session or self._settings.waha_session).strip() or self._settings.waha_session
        base = base_url_for_session(self._settings, name)
        return base, name

    def _session_base(self, session: str | None = None) -> str:
        base, name = self._resolve(session)
        return f"{base}/api/{name}"

    async def send_text(
        self,
        chat_id: str,
        text: str,
        reply_to: str | None = None,
        *,
        session: str | None = None,
    ) -> dict:
        base, name = self._resolve(session)
        payload: dict[str, str] = {
            "session": name,
            "chatId": chat_id,
            "text": text,
        }
        if reply_to:
            payload["reply_to"] = reply_to

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{base}/api/sendText",
                headers=self._headers(),
                json=payload,
            )
            if response.is_error:
                logger.error(
                    "WAHA sendText failed status=%s session=%s chatId=%s body=%s",
                    response.status_code,
                    name,
                    chat_id,
                    response.text[:500],
                )
            response.raise_for_status()
            data = response.json()
            logger.info("Sent WhatsApp message to %s via session %s", chat_id, name)
            return data

    async def delete_message(
        self,
        chat_id: str,
        message_id: str,
        *,
        session: str | None = None,
    ) -> None:
        """Delete/revoke a message via WAHA (sent messages = delete for everyone)."""
        chat_enc = quote(chat_id, safe="")
        msg_enc = quote(message_id, safe="")
        _, name = self._resolve(session)
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{self._session_base(name)}/chats/{chat_enc}/messages/{msg_enc}",
                headers=self._headers(),
            )
            if response.is_error:
                logger.error(
                    "WAHA deleteMessage failed status=%s session=%s chatId=%s messageId=%s body=%s",
                    response.status_code,
                    name,
                    chat_id,
                    message_id,
                    response.text[:500],
                )
            response.raise_for_status()
            logger.info("Deleted WhatsApp message %s in %s (session=%s)", message_id, chat_id, name)

    async def ping(self) -> bool:
        base, _ = self._resolve(None)
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{base}/api/sessions", headers=self._headers())
                return response.status_code < 500
        except httpx.HTTPError:
            return False

    @staticmethod
    def chat_list_params(*, limit: int, offset: int) -> dict[str, int | str]:
        """Query params for GET /api/{session}/chats (WAHA ChatSortField enum)."""
        return {
            "limit": limit,
            "offset": offset,
            "sortBy": "conversationTimestamp",
            "sortOrder": "desc",
        }

    async def list_chats(
        self, *, limit: int = 50, offset: int = 0, session: str | None = None
    ) -> list[dict]:
        params = self.chat_list_params(limit=limit, offset=offset)
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(
                f"{self._session_base(session)}/chats",
                headers=self._headers(),
                params=params,
            )
            if response.is_error:
                logger.error(
                    "WAHA list_chats failed status=%s url=%s body=%s",
                    response.status_code,
                    response.url,
                    response.text[:500],
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
        session: str | None = None,
    ) -> list[dict]:
        encoded = quote(chat_id, safe="")
        params = {"limit": limit, "offset": offset, "downloadMedia": "false"}
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(
                f"{self._session_base(session)}/chats/{encoded}/messages",
                headers=self._headers(),
                params=params,
            )
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                return data
            return list(data.get("messages") or data.get("data") or [])
