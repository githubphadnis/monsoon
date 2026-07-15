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
- kind: one of todo, note, done, list, digest, reflect, help, unknown
- title: string or null
- notes: string or null
- task_number: integer or null (for done/list by id)
- due_at: ISO8601 datetime string or null
- remind_at: ISO8601 datetime string or null
- status: inbox|today|waiting|scheduled or null
- priority: low|normal|high or null

Use kind=todo only for clear task creation. Use kind=unknown for questions
or conversational messages. No markdown. No explanation. JSON only."""

DIGEST_INSTRUCTION = (
    "You write Prakalp's personal *action digest* for WhatsApp.\n"
    "This is NOT customer support, NOT a meeting summary, NOT an inbox review.\n\n"
    "GOOD example:\n"
    "Open: finish Griham website/ppt by Saturday; buy PC for P3; fix bappa mandir lights. "
    "Call Hatim before 10:00 IST. Next: ship the website draft, then order the PC.\n\n"
    "BAD example (never do this):\n"
    "Thank you for reaching out. 1. Golf Meadows receipts… 2. WhatsApp messages… "
    "feel free to let me know if you need help.\n\n"
    "Rules:\n"
    "- Build the reply from ## Open tasks first. Use task titles verbatim.\n"
    "- 2–4 short WhatsApp paragraphs (or tight prose). Max ~900 characters.\n"
    "- End with 1–2 concrete next actions for today.\n"
    "- Optional email/WA signals: mention at most ONE only if it creates a today action.\n"
    "- NEVER thank the user, never 'reaching out' / 'queries' / 'feel free' / 'let me know'.\n"
    "- NEVER number-list inbox topics (receipts, insurance ads, greetings, society mail).\n"
    "- NEVER invent facts. NEVER dump phones/emails. NEVER lead with Task #N."
)

REFLECT_INSTRUCTION = (
    "Reflect on the named topic using only the provided context.\n"
    "Write flowing WhatsApp prose (2–3 short paragraphs) covering: what's active, "
    "blockers/risks, and one next step — not labeled staccato headers.\n"
    "CRITICAL: Stay on the topic. Use only tasks/notes that clearly match it.\n"
    "Do NOT merge unrelated open tasks into one story (e.g. dashcam SD card ≠ notebooks).\n"
    "If the context has nothing on-topic, say so briefly and suggest `todo …` — "
    "do not invent links or pad with other backlog items.\n"
    "Max ~1000 chars. Do not thank the user, invent facts, dump addresses/phones, "
    "or write customer-support fluff. Never lead with Task #N / #N / id:T."
)

ASK_INSTRUCTION = (
    "You are monsoon — a sharp, friendly assistant on WhatsApp, not a corporate bot. "
    "Answer like a helpful teammate: warm, specific, and short (1–3 paragraphs). "
    "Use the provided context when it helps; quote concrete titles or message snippets. "
    "If context is thin, say what you don't know and suggest `todo …`, `digest`, or "
    "`reflect <topic>`. Never thank the user, never dump phone/email lists, never invent facts."
)

_BAD_DIGEST_MARKERS = (
    "entities identified",
    "entity information",
    "entity information extraction",
    "*phone numbers*",
    "phone numbers:",
    "*email addresses*",
    "email addresses:",
    "thank you for sharing",
    "thank you for reaching out",
    "thanks for reaching out",
    "here's a summary",
    "here is a summary",
    "i'll respond to your queries",
    "i will respond to your queries",
    "in the order they were received",
    "feel free to",
    "let me know if you need",
    "if you need further assistance",
    "if you have any other specific",
    "please create a helpdesk",
    "greetings and wishing",
    "how can i assist",
    "happy to help",
)

_NUMBERED_TOPIC_RE = re.compile(r"(?m)^\s*\d+\.\s+\*")


def looks_like_bad_digest(text: str) -> bool:
    """True when the model wrote support-desk / inbox fluff instead of an action digest."""
    normalized = (text or "").strip()
    if not normalized:
        return True
    lower = normalized.lower()
    if any(marker in lower for marker in _BAD_DIGEST_MARKERS):
        return True
    if normalized.count("@") >= 5:
        return True
    # Numbered bold topic dump (1. *Foo*: … 2. *Bar*: …)
    if len(_NUMBERED_TOPIC_RE.findall(normalized)) >= 3:
        return True
    return False


def _extract_task_titles(context_text: str) -> list[str]:
    """Pull task titles from a ## Open tasks / ## Tasks section for grounding checks."""
    titles: list[str] = []
    in_tasks = False
    for line in (context_text or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            heading = stripped[3:].lower()
            in_tasks = heading.startswith("open tasks") or heading.startswith("tasks")
            continue
        if not in_tasks or not stripped:
            continue
        # "Title [status] due:… ref:T12"
        title = re.split(r"\s+\[", stripped, maxsplit=1)[0].strip()
        if title and not title.startswith("#") and len(title) >= 4:
            titles.append(title)
    return titles


def digest_mentions_tasks(text: str, context_text: str) -> bool:
    """False when open tasks exist but the reply ignores them entirely."""
    titles = _extract_task_titles(context_text)
    if not titles:
        return True
    lower = (text or "").lower()
    for title in titles:
        # Match on a distinctive chunk of the title (first 12+ chars or whole if short)
        chunk = title.strip().lower()
        if len(chunk) > 24:
            chunk = chunk[:24]
        if chunk and chunk in lower:
            return True
        # Also try significant words (≥5 chars)
        words = [w for w in re.findall(r"[a-z0-9]{5,}", chunk) if w not in {"about", "their", "there"}]
        if words and all(w in lower for w in words[:2]):
            return True
    return False


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
        model = self._settings.ollama_model_for("parse")
        try:
            async with httpx.AsyncClient(
                timeout=self._settings.ollama_timeout_for("parse")
            ) as client:
                response = await client.post(
                    f"{self._base}/api/chat",
                    json={
                        "model": model,
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
            logger.warning("Ollama parse failed (model=%s): %s", model, exc)
            return None

        return self._parse_json_content(content)

    async def generate_text(
        self,
        *,
        user_prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
        purpose: str = "chat",
    ) -> str | None:
        system = system_prompt or self._settings.monsoon_soul_prompt
        model = self._settings.ollama_model_for(purpose)
        payload: dict = {
            "model": model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
        }
        if temperature is not None:
            payload["options"] = {"temperature": temperature}
        try:
            async with httpx.AsyncClient(
                timeout=self._settings.ollama_timeout_for(purpose)
            ) as client:
                response = await client.post(
                    f"{self._base}/api/chat",
                    json=payload,
                )
                response.raise_for_status()
                return response.json()["message"]["content"]
        except (httpx.HTTPError, KeyError, json.JSONDecodeError) as exc:
            logger.warning("Ollama generate failed (model=%s): %s", model, exc)
            return None

    async def generate_digest(self, *, context_text: str, now_iso: str) -> str | None:
        system = f"{self._settings.monsoon_soul_prompt}\n\n{DIGEST_INSTRUCTION}"
        user_prompt = (
            f"Current time: {now_iso}\n\n"
            "Write today's action digest from the Open tasks section.\n"
            "Do not summarize email/WhatsApp as numbered topics.\n\n"
            f"Context:\n{context_text}"
        )
        text = await self.generate_text(
            user_prompt=user_prompt,
            system_prompt=system,
            temperature=0.2,
            purpose="chat",
        )
        if not text:
            return None
        if looks_like_bad_digest(text):
            logger.warning("Ollama digest rejected as fluff/inbox dump")
            return None
        if not digest_mentions_tasks(text, context_text):
            logger.warning("Ollama digest rejected — ignored open tasks")
            return None
        return text

    async def generate_reflect(
        self, *, topic: str, context_text: str, now_iso: str
    ) -> str | None:
        system = f"{self._settings.monsoon_soul_prompt}\n\n{REFLECT_INSTRUCTION}"
        user_prompt = (
            f"Topic: {topic}\nCurrent time: {now_iso}\n\nContext:\n{context_text}"
        )
        text = await self.generate_text(
            user_prompt=user_prompt,
            system_prompt=system,
            temperature=0.3,
            purpose="chat",
        )
        if text and looks_like_bad_digest(text):
            logger.warning("Ollama reflect rejected as fluff/inbox dump")
            return None
        return text

    async def generate_ask(
        self, *, question: str, context_text: str, now_iso: str
    ) -> str | None:
        system = f"{self._settings.monsoon_soul_prompt}\n\n{ASK_INSTRUCTION}"
        user_prompt = (
            f"Current time: {now_iso}\n\nContext:\n{context_text}\n\n"
            f"Question:\n{question.strip()}"
        )
        return await self.generate_text(
            user_prompt=user_prompt,
            system_prompt=system,
            temperature=0.4,
            purpose="chat",
        )

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
