"""Ollama client for structured task parsing."""

import json
import logging
import re
from datetime import datetime

import httpx

from app.config import Settings
from app.schemas.capture import ParsedCapture

logger = logging.getLogger("monsoon.ollama")

PARSE_PROMPT = """You parse personal capture messages into JSON only.
Return a single JSON object with keys:
- kind: one of todo, note, done, list, digest, help, unknown
- title: string or null
- notes: string or null
- task_number: integer or null (for done/list by id)
- due_at: ISO8601 datetime string or null
- remind_at: ISO8601 datetime string or null
- status: inbox|today|waiting|scheduled or null
- priority: low|normal|high or null

No markdown. No explanation. JSON only."""


class OllamaClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base = settings.ollama_base_url.rstrip("/")

    async def ping(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self._base}/api/tags")
                return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def parse_capture(self, text: str, now_iso: str) -> ParsedCapture | None:
        user_prompt = (
            f"Current time ({self._settings.app_timezone}): {now_iso}\n"
            f"Message: {text.strip()}"
        )
        try:
            async with httpx.AsyncClient(timeout=float(self._settings.ollama_timeout_seconds)) as client:
                response = await client.post(
                    f"{self._base}/api/chat",
                    json={
                        "model": self._settings.ollama_model,
                        "stream": False,
                        "format": "json",
                        "messages": [
                            {"role": "system", "content": PARSE_PROMPT},
                            {"role": "user", "content": user_prompt},
                        ],
                    },
                )
                response.raise_for_status()
                content = response.json()["message"]["content"]
        except (httpx.HTTPError, KeyError, json.JSONDecodeError) as exc:
            logger.warning("Ollama parse failed: %s", exc)
            return None

        return self._parse_json_content(content)

    def _parse_json_content(self, content: str) -> ParsedCapture | None:
        try:
            raw = json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if not match:
                return None
            try:
                raw = json.loads(match.group(0))
            except json.JSONDecodeError:
                return None

        for field in ("due_at", "remind_at"):
            value = raw.get(field)
            if value:
                try:
                    raw[field] = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
                except ValueError:
                    raw[field] = None

        try:
            return ParsedCapture.model_validate(raw)
        except Exception as exc:
            logger.warning("Invalid Ollama parse payload: %s", exc)
            return None
