# Operator runbook — LLM Phase A (2026-07-08)

**Orchestrator:** Cursor agent in `C:\projects\monsoon` on branch `feature/llm-phase-a`.  
**You:** Run OpenCode + notcoolio WA pilot exactly as numbered below.  
**OpenCode:** Implementation only — no git commit/push.

Check `STATUS.md` before each step. Report back to Cursor with: **step number + "done" + any errors**.

---

## Phase 0 — Cursor already did (you do nothing)

- [x] Committed parallel-work docs on `main` (`f2585f3`)
- [x] Created branch `feature/llm-phase-a` in `C:\projects\monsoon`
- [x] Created worktrees:
  - `C:\projects\monsoon-oc01` → branch `oc/01-context-slice`
  - `C:\projects\monsoon-oc02` → branch `oc/02-ollama-contributions`
- [x] `monsoon-oc03` **not** created yet (waits for OC-01 + OC-02 merge)

---

## Phase 1 — OpenCode OC-01 — **SKIP (Cursor shipped)**

> Cursor implemented OC-01 on `feature/llm-phase-a`. Do not run unless you want a second opinion.

## Phase 2 — OpenCode OC-02 — **SKIP (Cursor shipped)**

> Cursor implemented OC-02 on `feature/llm-phase-a`.

## Phase 3 — WA backfill pilot (notcoolio) — **YOUR ONLY REQUIRED ACTION**

SSH to notcoolio (your usual method), then:

```bash
curl -s http://127.0.0.1:8080/health/webhook | python3 -m json.tool
docker exec monsoon-app python infra/scripts/wa_backfill.py --max-chats 5
curl -s http://127.0.0.1:8080/health/wa-index | python3 -m json.tool
```

**Report to Cursor:** `Phase 3 done` + JSON from wa-index (or errors)

---

## Phase 4 — Wait for Cursor merge

Cursor will:

- Review OC-01 and OC-02 diffs
- Merge into `feature/llm-phase-a`
- Run full pytest
- Create/update `monsoon-oc03` worktree
- Tell you when to run **Phase 5**

**You do nothing** until Cursor messages: **"Start Phase 5"**

---

## Phase 5 — OpenCode OC-03 — **SKIP (Cursor shipped)**

## Phase 6 — Deploy (after Cursor merges to main / GHCR)

Cursor will give exact Portainer / pull steps when `feature/llm-phase-a` is ready.

Smoke on WhatsApp:

- `digest`
- `reflect griham` (or any topic you have data for)
- `todo orchestration smoke test`

---

## If something breaks

| Problem | Action |
|---------|--------|
| OpenCode edited wrong files | Stop. Report to Cursor. Do not commit. |
| pytest fails | Paste full pytest output to Cursor |
| merge conflict | Stop. Cursor resolves in integrator folder |
| OpenCode wants to commit | Refuse — orchestrator owns git |
