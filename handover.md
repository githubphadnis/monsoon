# Handover — monsoon

## Last worked on

2026-07-12 — family model realign; `@assign`; `delete`; ephemeral; Ollama Auto.

## Current state / WIP

- **Family:** see `docs/family-model.md` (roster + single-WAHA truth).
- **Assign:** `MONSOON_USER_ALIASES` + `todo @rashmi …`
- **Ephemeral** WA message cleanup (default 5 min).
- **LLM** optional parse/chat model split.

## Operator priorities

1. Redeploy `main`.
2. Portainer env from `docs/family-model.md` (numbers, chat JIDs, aliases, shared group).
3. Smoke: Rashmi 1:1 with monsoon number; family `@prakalp …`; personal `digest`.
4. Optional: `OLLAMA_MODEL_CHAT=qwen2.5:14b` on lenai.

## Next product work

- MS-09 multi-WAHA (true Message yourself per person) — if still desired
- Notify assignee on `@assign` (DM ping)
- Group RAG / lunch memory
- MS-08 snooze

## Environment

| Host | Role |
|------|------|
| `notcoolio` | monsoon Portainer stack |
| `lenai` | Ollama |
