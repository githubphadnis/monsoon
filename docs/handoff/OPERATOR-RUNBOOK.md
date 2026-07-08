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

## Phase 1 — OpenCode #1 (OC-01) — **DO NOW**

1. Open **OpenCode Desktop**
2. **File → Open Folder** → `C:\projects\monsoon-oc01` (not `monsoon`)
3. Confirm you see `AGENTS.md` at the root
4. Open `docs/handoff/oc-01-context-slice.md`
5. Copy **from line `## Guardrails`** through the end of the file
6. Paste into OpenCode chat. **Prepend this exact line:**

   ```text
   ORCHESTRATOR DIRECTIVE OC-01: Implement exactly per brief. Exclusive files only. pytest tests/test_context_slice.py -q must pass. Do NOT commit or push. When finished reply: OC-01 COMPLETE and list files changed.
   ```

7. Let OpenCode run to completion
8. In PowerShell verify:

   ```powershell
   cd C:\projects\monsoon-oc01
   git status -sb
   git diff --stat
   pytest tests/test_context_slice.py -q
   ```

9. **Report to Cursor:** `Phase 1 done` + paste `git diff --stat` output (or errors)

**Do not** start Phase 2 until Cursor says Phase 1 reviewed (or run Phase 2 in parallel — see Phase 2).

---

## Phase 2 — OpenCode #2 (OC-02) — **DO IN PARALLEL WITH Phase 1**

1. Open a **second** OpenCode window (or new session)
2. **Open Folder** → `C:\projects\monsoon-oc02`
3. Open `docs/handoff/oc-02-ollama-contributions.md`
4. Copy from `## Guardrails` to end. Prepend:

   ```text
   ORCHESTRATOR DIRECTIVE OC-02: Implement exactly per brief. Do not break parse_capture. pytest tests/test_ollama_contributions.py tests/test_parser.py -q must pass. Do NOT commit or push. When finished reply: OC-02 COMPLETE and list files changed.
   ```

5. Verify:

   ```powershell
   cd C:\projects\monsoon-oc02
   git status -sb
   git diff --stat
   pytest tests/test_ollama_contributions.py tests/test_parser.py -q
   ```

6. **Report to Cursor:** `Phase 2 done` + `git diff --stat`

---

## Phase 3 — WA backfill pilot (notcoolio) — **DO IN PARALLEL WITH Phases 1–2**

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

## Phase 5 — OpenCode #3 (OC-03) — **ONLY AFTER CURSOR SAYS GO**

1. **Open Folder** → `C:\projects\monsoon-oc03`
2. Open `docs/handoff/oc-03-capture-reflect-digest.md`
3. Copy from `## Guardrails` to end. Prepend:

   ```text
   ORCHESTRATOR DIRECTIVE OC-03: OC-01 and OC-02 are merged in this tree. Implement exactly per brief. pytest tests/test_capture_llm.py tests/test_parser.py -q must pass. Do NOT commit or push. When finished reply: OC-03 COMPLETE.
   ```

4. Verify:

   ```powershell
   cd C:\projects\monsoon-oc03
   pytest tests/test_capture_llm.py tests/test_parser.py -q
   git diff --stat
   ```

5. **Report to Cursor:** `Phase 5 done` + diff stat

---

## Phase 6 — Deploy (after Cursor merges all)

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
