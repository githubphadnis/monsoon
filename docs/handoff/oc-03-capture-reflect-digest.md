# OpenCode offload brief — capture reflect + LLM digest (OC-03)

> **Run only after OC-01 and OC-02 are merged** into your integrator branch (or cherry-pick
> those files into `monsoon-oc03` first). Paste from **Guardrails** down into **OpenCode Desktop**
> with folder `C:\projects\monsoon-oc03`. **Do not commit or push.**

## Guardrails (always)

- Repo: `C:/projects/monsoon-oc03` · Branch: `oc/03-capture-reflect-digest` · **DO NOT commit or push.**
- Depends on OC-01 (`context_slice`) and OC-02 (`generate_digest`, `generate_reflect`).
- If those files are missing, **stop** and report blocker — do not reimplement them here.

## Goal

Wire LLM contributions into WhatsApp capture: **`reflect <topic>`** command and **LLM-powered
`digest`** with SQL fallback when Ollama is down.

## Read first

1. `docs/llm-integration.md`
2. `app/services/capture_service.py` — `_digest`, `_dispatch`, `HELP_TEXT`
3. `app/services/parser.py` — regex patterns
4. `app/schemas/capture.py` — `ParsedCapture`
5. `app/services/context_slice.py` — `build_context_slice` (from OC-01)
6. `app/integrations/ollama/client.py` — `generate_digest`, `generate_reflect` (from OC-02)

## Do

1. **`app/schemas/capture.py`**
   - Add `reflect_topic: str | None = None` to `ParsedCapture` (optional field)

2. **`app/services/parser.py`**
   - Add `REFLECT_RE = re.compile(r"^reflect\s+(.+)$", re.IGNORECASE)`
   - Match → `ParsedCapture(kind="reflect", reflect_topic=group(1).strip())`
   - Place before generic todo fallback

3. **`app/services/capture_service.py`**
   - Import `build_context_slice`, `ContextSliceRequest`, `OllamaClient`
   - `_dispatch`: handle `parsed.kind == "reflect"` → `await self._reflect(user, parsed.reflect_topic)`
   - **`_reflect`:** build slice with topic; call `ollama.generate_reflect`; fallback message if None
   - **`_digest`:** build slice (no topic); try `ollama.generate_digest`; on None keep existing SQL list behavior
   - Update `HELP_TEXT` with: `reflect <topic>   what's active on a topic`

4. **`tests/test_capture_llm.py`** (new)
   - Mock Ollama + DB: digest returns LLM text when mock succeeds
   - Mock Ollama down: digest returns SQL list format
   - `reflect griham` parses and dispatches (mock generate_reflect)

## Constraints

**Exclusive files:**

- `app/services/parser.py`
- `app/services/capture_service.py`
- `app/schemas/capture.py`
- `tests/test_capture_llm.py` (new)

**Do not touch:** `context_slice.py`, `ollama/client.py` (read-only imports).

## Output

- [ ] HELP_TEXT updated
- [ ] Fail-open digest when Ollama unreachable
- [ ] **Coverage metadata**

## Completeness checklist

- [ ] `reflect bank` → reflect flow (not a new task)
- [ ] `digest` uses LLM when available
- [ ] `digest` falls back to current list when Ollama returns None
- [ ] Existing capture tests still pass

## Acceptance criteria

- [ ] `pytest tests/test_capture_llm.py tests/test_parser.py -q` passes
- [ ] `git diff --name-only` shows only exclusive files
- [ ] `help` output mentions `reflect`
