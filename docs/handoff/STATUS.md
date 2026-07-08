# Handoff lock board

**Updated:** 2026-07-08 06:55 — orchestration live

**Orchestrator:** Cursor @ `C:\projects\monsoon` · branch `feature/llm-phase-a`  
**Operator runbook:** [OPERATOR-RUNBOOK.md](./OPERATOR-RUNBOOK.md)

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
| OC-01 | [oc-01-context-slice.md](./oc-01-context-slice.md) | `oc/01-context-slice` / `monsoon-oc01` | **IN PROGRESS** | OpenCode (you) | `context_slice.py`, `schemas/context.py`, `test_context_slice.py` |
| OC-02 | [oc-02-ollama-contributions.md](./oc-02-ollama-contributions.md) | `oc/02-ollama-contributions` / `monsoon-oc02` | **IN PROGRESS** | OpenCode (you) | `ollama/client.py`, `test_ollama_contributions.py` |
| OC-03 | [oc-03-capture-reflect-digest.md](./oc-03-capture-reflect-digest.md) | `monsoon-oc03` (not created yet) | BLOCKED | — | `parser.py`, `capture_service.py`, `schemas/capture.py`, `test_capture_llm.py` |
| CUR-01 | Integration | `feature/llm-phase-a` / `monsoon` | IN PROGRESS | Cursor | merge + docs + pytest |

**OC-03 unblock:** after OC-01 and OC-02 merged to `feature/llm-phase-a`.

## Operator (human)

| Task | Status | Notes |
|------|--------|-------|
| Phase 1 — OpenCode OC-01 in `monsoon-oc01` | **DO NOW** | See OPERATOR-RUNBOOK Phase 1 |
| Phase 2 — OpenCode OC-02 in `monsoon-oc02` | **DO NOW** (parallel) | See OPERATOR-RUNBOOK Phase 2 |
| Phase 3 — WA backfill on notcoolio | **DO NOW** (parallel) | `--max-chats 5` |
| Phase 5 — OpenCode OC-03 | BLOCKED | Wait for Cursor |

## Merge log

| When | Branch | Merged by | pytest |
|------|--------|-----------|--------|
| 2026-07-08 | `main` ← orchestration docs | Cursor | n/a |
| — | `feature/llm-phase-a` ← oc/01 | pending | — |
| — | `feature/llm-phase-a` ← oc/02 | pending | — |
