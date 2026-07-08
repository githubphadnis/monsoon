"""WorkFlowy HTTP client (beta API)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import Settings

logger = logging.getLogger("monsoon.workflowy")

WORKFLOWY_API_BASE = "https://beta.workflowy.com"


class WorkFlowyNotConfiguredError(RuntimeError):
    """Raised when WorkFlowy API key is missing."""


class WorkFlowyClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base = WORKFLOWY_API_BASE

    @property
    def configured(self) -> bool:
        return bool(self._settings.workflowy_api_key)

    def _headers(self) -> dict[str, str]:
        if not self.configured:
            raise WorkFlowyNotConfiguredError("WORKFLOWY_API_KEY is not set")
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._settings.workflowy_api_key}",
        }

    async def create_node(
        self,
        parent_id: str,
        name: str,
        *,
        layout_mode: str | None = None,
        note: str | None = None,
        position: str = "bottom",
    ) -> str | None:
        if not self.configured:
            logger.debug("WorkFlowy create_node skipped — no API key")
            return None

        payload: dict[str, Any] = {
            "parent_id": parent_id,
            "name": name,
            "position": position,
        }
        if layout_mode:
            payload["layoutMode"] = layout_mode
        if note:
            payload["note"] = note

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self._base}/api/v1/nodes",
                headers=self._headers(),
                json=payload,
            )
            if response.is_error:
                logger.error(
                    "WorkFlowy create_node failed status=%s parent=%s body=%s",
                    response.status_code,
                    parent_id,
                    response.text[:500],
                )
            response.raise_for_status()
            data = response.json()
            node_id = data.get("item_id") or data.get("id")
            return str(node_id) if node_id else None

    async def create_child(self, parent_id: str, name: str, *, position: str = "bottom") -> str | None:
        return await self.create_node(parent_id, name, position=position)

    async def complete_node(self, node_id: str) -> bool:
        if not self.configured:
            logger.debug("WorkFlowy complete_node skipped — no API key")
            return False

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self._base}/api/v1/nodes/{node_id}/complete",
                headers=self._headers(),
            )
            if response.is_error:
                logger.error(
                    "WorkFlowy complete_node failed status=%s node=%s body=%s",
                    response.status_code,
                    node_id,
                    response.text[:500],
                )
            response.raise_for_status()
            return True

    async def list_nodes(self, parent_id: str) -> list[dict[str, Any]]:
        if not self.configured:
            logger.debug("WorkFlowy list_nodes skipped — no API key")
            return []

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self._base}/api/v1/nodes",
                headers=self._headers(),
                params={"parent_id": parent_id},
            )
            if response.is_error:
                logger.error(
                    "WorkFlowy list_nodes failed status=%s parent=%s body=%s",
                    response.status_code,
                    parent_id,
                    response.text[:500],
                )
            response.raise_for_status()
            data = response.json()
            nodes = data.get("nodes")
            return list(nodes) if isinstance(nodes, list) else []
