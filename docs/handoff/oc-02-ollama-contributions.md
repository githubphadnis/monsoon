# OpenCode offload brief — Ollama contributions client (OC-02)

> Paste everything from **Guardrails** down into **OpenCode Desktop** with folder
> `C:\projects\monsoon-oc02` (branch `oc/02-ollama-contributions`). **Do not commit or push.**

## Guardrails (always)

- Repo: `C:/projects/monsoon-oc02` · Branch: `oc/02-ollama-contributions` · **DO NOT commit or push.**
- Follow `AGENTS.md`. Exclusive files only.
- **Preserve** existing `parse_capture` behavior — add new methods, do not break parse tests.
- **No secrets.**

## Goal

Extend `OllamaClient` so monsoon can generate **life-assistant contributions** (digest, reflect)
using `MONSOON_SOUL_PROMPT` as the system message — not only the rigid parse JSON prompt.

## Read first

1. `docs/llm-integration.md` — soul prompt, digest/enrich stages
2. `app/integrations/ollama/client.py` — existing `parse_capture`, `ping`
3. `app/config.py` — `monsoon_soul_prompt`, `ollama_*`
4. `tests/test_parser.py` — ensure parse still works after your edits

## Do

1. In `app/integrations/ollama/client.py`, add:

   **`async def generate_text(self, *, user_prompt: str, system_prompt: str | None = None) -> str | None`**
   - POST `/api/chat`, `stream: false`, no `format: json`
   - System = `system_prompt` or `settings.monsoon_soul_prompt`
   - Return assistant message content or `None` on failure (log warning, fail open)

   **`async def generate_digest(self, *, context_text: str, now_iso: str) -> str | None`**
   - System: soul prompt + short instruction: "Summarize open work. Lead with what matters today.
     End with 1-2 concrete next steps. Max 800 chars. WhatsApp-friendly plain text."
   - User: `Current time: {now_iso}\n\nContext:\n{context_text}`

   **`async def generate_reflect(self, *, topic: str, context_text: str, now_iso: str) -> str | None`**
   - System: soul prompt + "User asked for reflection on a topic. Be factual to context only.
     Structure: (1) what's active (2) blockers/risks (3) one suggested next step. Max 1000 chars."
   - User: topic + context

2. Keep `PARSE_PROMPT` separate — `parse_capture` must still use parse-only system prompt.

3. Create `tests/test_ollama_contributions.py`:
   - Mock `httpx.AsyncClient` (patch at module level like other tests if pattern exists)
   - Test `generate_text` returns content on 200 JSON
   - Test `generate_digest` includes soul-related system message path
   - Test failure returns `None` (fail open)

## Constraints

**Exclusive files:**

- `app/integrations/ollama/client.py`
- `tests/test_ollama_contributions.py` (new)

**Do not touch:** `context_slice.py`, `capture_service.py`, `parser.py`.

## Output

- [ ] Methods added without breaking `parse_capture`
- [ ] **Coverage metadata:** tests added, open questions

## Completeness checklist

- [ ] `parse_capture` unchanged in behavior (run existing parser tests)
- [ ] `generate_digest` / `generate_reflect` use `monsoon_soul_prompt` by default
- [ ] All new methods fail open (`None` + log on error)

## Acceptance criteria

- [ ] `pytest tests/test_ollama_contributions.py tests/test_parser.py -q` passes
- [ ] `git diff --name-only` shows only exclusive files
- [ ] `parse_capture` still uses `PARSE_PROMPT`, not soul prompt
