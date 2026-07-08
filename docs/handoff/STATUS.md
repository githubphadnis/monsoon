# Handoff lock board

**Updated:** 2026-07-08 — LLM Phase A parallel tracks

Update this file **before** starting a track. Only one agent per row in `IN PROGRESS`.

## Legend

| Status | Meaning |
|--------|---------|
| `READY` | Brief written; safe to start |
| `IN PROGRESS` | Agent active — do not touch exclusive files |
| `REVIEW` | Done; Cursor reviewing diff |
| `DONE` | Merged to `feature/llm-phase-a` |
| `BLOCKED` | Waiting on dependency |

## Tracks

| ID | Brief | Branch / folder | Status | Agent | Exclusive files |
|----|-------|-----------------|--------|-------|-----------------|
| OC-01 | [oc-01-context-slice.md](./oc-01-context-slice.md) | `oc/01-context-slice` / `monsoon-oc01` | READY | — | `context_slice.py`, `schemas/context.py`, `test_context_slice.py` |
| OC-02 | [oc-02-ollama-contributions.md](./oc-02-ollama-contributions.md) | `oc/02-ollama-contributions` / `monsoon-oc02` | READY | — | `ollama/client.py`, `test_ollama_contributions.py` |
| OC-03 | [oc-03-capture-reflect-digest.md](./oc-03-capture-reflect-digest.md) | `oc/03-capture-reflect-digest` / `monsoon-oc03` | BLOCKED | — | `parser.py`, `capture_service.py`, `schemas/capture.py`, `test_capture_llm.py` |
| CUR-01 | Integration | `feature/llm-phase-a` / `monsoon` | READY | Cursor | docs + merge |

**OC-03 unblock:** after OC-01 and OC-02 are `DONE` (or merged to integrator branch).

## Operator (human)

| Task | Status | Notes |
|------|--------|-------|
| WA backfill `--max-chats 5` on notcoolio | READY | Independent of code tracks |
| Gmail OAuth | DEFERRED | — |

## Merge log

| When | Branch | Merged by | pytest |
|------|--------|-----------|--------|
| — | — | — | — |
