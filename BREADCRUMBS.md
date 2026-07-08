# BREADCRUMBS — monsoon

**Updated:** 2026-07-08 06:55 — orchestration LIVE

## YOUR actions right now (operator)

Open **`docs/handoff/OPERATOR-RUNBOOK.md`** and run **Phase 1 + Phase 2 + Phase 3 in parallel**.

Report back: `Phase 1 done`, `Phase 2 done`, `Phase 3 done` (with diff stat / errors).

## Cursor (integrator) state

- Branch: `feature/llm-phase-a` @ `C:\projects\monsoon`
- Worktrees: `monsoon-oc01`, `monsoon-oc02` ready for OpenCode
- Waiting: OC-01 + OC-02 completion → merge → create `monsoon-oc03` → OC-03

## Git

- `main` @ `f2585f3` — orchestration docs committed
- `feature/llm-phase-a` — integrator (same commit, merges land here)

## Defer

- Gmail OAuth
- OC-03 until 01+02 merged
- Push to origin until integration reviewed
