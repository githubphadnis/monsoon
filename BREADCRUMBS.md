# BREADCRUMBS — monsoon

**Updated:** 2026-07-08

## Next action (start here)

### Operator (you)

1. WA pilot on notcoolio: `docker exec monsoon-app python infra/scripts/wa_backfill.py --max-chats 5`
2. Check: `curl -s http://127.0.0.1:8080/health/wa-index`

### Parallel dev (Cursor + OpenCode)

1. Read `docs/parallel-work.md` — create worktrees `monsoon-oc01`, `oc02`, `oc03`.
2. Update `docs/handoff/STATUS.md` → set OC-01 / OC-02 to `IN PROGRESS`.
3. Paste briefs into OpenCode Desktop (**OC-01 and OC-02 in parallel**).
4. Cursor merges to `feature/llm-phase-a`, then unblocks OC-03.
5. Cursor runs full `pytest`, updates `docs/llm-integration.md`, session docs.

**Defer:** Gmail OAuth until WA pilot succeeds.

## Direction

**LLM Phase A** — context slice + soul-powered digest + `reflect <topic>` (life assistant, not todo-only).
OpenLoomi patterns: SQL context bundle, insight-style contributions (`docs/context-atlas.md`).

## Branch / state

- `main` — deployed on notcoolio; WA backfill fixes on main.
- `feature/llm-phase-a` — integrator branch (create when merging OC tracks).
- Handoff docs written; code tracks **not started** yet.
