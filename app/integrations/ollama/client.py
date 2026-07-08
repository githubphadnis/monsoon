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

DIGEST_INSTRUCTION = (
    "You are writing a personal action digest for WhatsApp — not a meeting summary. "
    "Rules:\n"
    "- Lead with 2–4 concrete items by task title / email subject / WA thread — never invent.\n"
    "- Prefer open tasks first; pull in email/WA only when it clearly relates or is time-sensitive.\n"
    "- End with exactly 1–2 next actions the user can do today.\n"
    "- Max 700 chars. Plain text. Short lines OK.\n"
    "- NEVER: thank the user, say 'here's a summary', categorize into Insurance/Health/"
    "Personal Communication buckets, list raw emails/phones, or offer further assistance.\n"
    "- NEVER lead with 'Task #N', '#N', or 'id:T'."
)

REFLECT_INSTRUCTION = (
    "Reflect on the named topic using only the provided context. "
    "Structure: (1) what's active — name concrete items (2) blockers/risks "
    "(3) one next step. Max 900 chars. Plain WhatsApp text. "
    "Do not thank the user, do not invent facts, do not dump addresses/phones. "
    "Never lead with 'Task #N', '#N', or 'id:T'."
)


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

    async def generate_text(
        self, *, user_prompt: str, system_prompt: str | None = None
    ) -> str | None:
        system = system_prompt or self._settings.monsoon_soul_prompt
        try:
            async with httpx.AsyncClient(
                timeout=float(self._settings.ollama_timeout_seconds)
            ) as client:
                response = await client.post(
                    f"{self._base}/api/chat",
                    json={
                        "model": self._settings.ollama_model,
                        "stream": False,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user_prompt},
                        ],
                    },
                )
                response.raise_for_status()
                return response.json()["message"]["content"]
        except (httpx.HTTPError, KeyError, json.JSONDecodeError) as exc:
            logger.warning("Ollama generate failed: %s", exc)
            return None

    async def generate_digest(self, *, context_text: str, now_iso: str) -> str | None:
        system = f"{self._settings.monsoon_soul_prompt}\n\n{DIGEST_INSTRUCTION}"
        user_prompt = f"Current time: {now_iso}\n\nContext:\n{context_text}"
        return await self.generate_text(user_prompt=user_prompt, system_prompt=system)

    async def generate_reflect(
        self, *, topic: str, context_text: str, now_iso: str
    ) -> str | None:
        system = f"{self._settings.monsoon_soul_prompt}\n\n{REFLECT_INSTRUCTION}"
        user_prompt = (
            f"Topic: {topic}\nCurrent time: {now_iso}\n\nContext:\n{context_text}"
        )
        return await self.generate_text(user_prompt=user_prompt, system_prompt=system)

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
