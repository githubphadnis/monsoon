# OpenCode offload brief — context slice service (OC-01)

> Paste everything from **Guardrails** down into **OpenCode Desktop** with folder
> `C:\projects\monsoon-oc01` (branch `oc/01-context-slice`). **Do not commit or push.**

## Guardrails (always)

- Repo: `C:/projects/monsoon-oc01` · Branch: `oc/01-context-slice` · **DO NOT commit or push.**
- Follow `AGENTS.md`. Exclusive files only (listed below).
- **No secrets.** No edits to `.env`, deploy compose, or WAHA config.
- If you need to change `capture_service.py` or `ollama/client.py`, **stop** — those are other tracks.

## Goal

Implement a **context slice** builder: given a `user_id` and optional topic, assemble a
bounded text bundle from Postgres (tasks + indexed WA messages + entities) for LLM calls.
This is monsoon's OpenLoomi-inspired "SQL bundle, not graph DB" pattern — see
`docs/context-atlas.md` and `docs/llm-integration.md`.

## Read first

1. `docs/context-atlas.md` — layer model, context slice concept
2. `docs/llm-integration.md` — LLM responsibilities
3. `app/models/tables.py` — `Task`, `WaMessage`, `WaChat`, `ExtractedEntity`
4. `app/config.py` — `app_timezone`, `waha_session`
5. `tests/test_parser.py` — pytest style in this repo

## Do

1. Create `app/schemas/context.py`:
   - `ContextSlice` pydantic model: `tasks_text`, `wa_messages_text`, `entities_text`, `topic`, `char_count`
   - `ContextSliceRequest`: `user_id: UUID`, `topic: str | None = None`, `max_chars: int = 12000`

2. Create `app/services/context_slice.py`:
   - `build_context_slice(db: Session, settings: Settings, request: ContextSliceRequest) -> ContextSlice`
   - **Tasks section:** open tasks (`status != 'done'`), order by `display_number` desc, limit 20.
     Format: `#N title [status] due:… notes:…`
   - **WA section:** if `wa_messages` has rows for `settings.waha_session`, include last 30 messages
     (join `wa_chats` for chat name). If `topic` set, filter messages where `body ILIKE %topic%`
     OR chat `name ILIKE %topic%` (case-insensitive).
   - **Entities section:** last 20 `extracted_entities` linked to those message ids (or all recent if no topic).
   - **Budget:** truncate sections oldest-first until total ≤ `max_chars`; set `char_count`.
   - Pure SQLAlchemy — no HTTP, no Ollama calls.

3. Create `tests/test_context_slice.py`:
   - Use in-memory or test DB pattern from `tests/test_db.py` if available; else mock Session with fixtures.
   - At minimum: empty DB returns empty sections; tasks appear in output; topic filter reduces WA lines.

4. Export from `app/services/__init__.py` only if other modules already re-export services (match convention).

## Constraints

**Exclusive files (only these may change):**

- `app/services/context_slice.py` (new)
- `app/schemas/context.py` (new)
- `tests/test_context_slice.py` (new)

**Do not touch:** `capture_service.py`, `parser.py`, `ollama/client.py`, `models/tables.py`.

## Output

- [ ] Files created: paths above
- [ ] **Coverage metadata:** models read, test cases added, open questions
- [ ] Checklist below complete

## Completeness checklist

- [ ] `build_context_slice` returns all four text sections + `char_count`
- [ ] Topic filter applies to WA body and chat name
- [ ] `max_chars` enforced with truncation
- [ ] No network calls in service layer

## Acceptance criteria

- [ ] `pytest tests/test_context_slice.py -q` passes
- [ ] `git diff --name-only` shows only exclusive files (+ optional `app/services/__init__.py`)
- [ ] `rg "httpx|ollama" app/services/context_slice.py` returns 0 matches
