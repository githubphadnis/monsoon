# Parallel work — Cursor + OpenCode

Fast multi-agent development on monsoon without stepping on each other.

**Orchestrator:** Cursor agent (reviews all diffs, integrates, updates session docs).  
**Workers:** OpenCode Desktop (DeepSeek or your chosen model) — one brief per session.  
**Courier:** You paste briefs, run agents, merge branches.

Rationale mirrors griham `dev-docs.md §1.10` (manual handoff model).

---

## Golden rules

1. **One owner per file** — briefs list exclusive paths; never two agents edit the same file.
2. **Lock board first** — update `docs/handoff/STATUS.md` before starting any track.
3. **Branches or worktrees** — never two agents on `main` in the same folder.
4. **No unreviewed commits** — OpenCode must **not** commit or push; Cursor reviews `git diff`.
5. **Document every track** — each brief ends with checklist + coverage metadata; session docs updated when merged.
6. **Secrets stay out** — no `.env`, WAHA keys, Gmail tokens, or production URLs in briefs.

---

## Setup (recommended: git worktrees)

Isolates OpenCode from Cursor so saves and file watchers do not fight.

```powershell
cd C:\projects\monsoon
git fetch origin
git checkout main
git pull origin main

# One worktree per parallel track (folders sit beside monsoon/)
git worktree add C:\projects\monsoon-oc01 -b oc/01-context-slice
git worktree add C:\projects\monsoon-oc02 -b oc/02-ollama-contributions
git worktree add C:\projects\monsoon-oc03 -b oc/03-capture-reflect-digest
```

| Tool | Open folder | Branch |
|------|-------------|--------|
| **Cursor** | `C:\projects\monsoon` | `main` or `feature/llm-phase-a` (integrator) |
| **OpenCode #1** | `C:\projects\monsoon-oc01` | `oc/01-context-slice` |
| **OpenCode #2** | `C:\projects\monsoon-oc02` | `oc/02-ollama-contributions` |
| **OpenCode #3** | `C:\projects\monsoon-oc03` | `oc/03-capture-reflect-digest` |

**Merge order** (dependencies):

```text
oc/01-context-slice  ──┐
                       ├──► feature/llm-phase-a (Cursor integrates + pytest)
oc/02-ollama-contributions ──┘
         │
         ▼
oc/03-capture-reflect-digest
```

```powershell
cd C:\projects\monsoon
git checkout -b feature/llm-phase-a
git merge oc/01-context-slice
git merge oc/02-ollama-contributions
pytest
git merge oc/03-capture-reflect-digest
pytest
```

Remove worktrees when done:

```powershell
git worktree remove C:\projects\monsoon-oc01
git worktree remove C:\projects\monsoon-oc02
git worktree remove C:\projects\monsoon-oc03
```

---

## Setup (lighter: single folder, sequential)

If worktrees feel heavy today:

1. Run **one** OpenCode brief at a time on `C:\projects\monsoon`.
2. **Close the repo in Cursor** (or close edited files) before OpenCode saves.
3. After each brief: `git diff` → Cursor review → commit to a feature branch → next brief.

Do **not** run two OpenCode sessions on the same folder.

---

## OpenCode configuration

1. **Open the correct worktree** — File → Open Folder → `monsoon-oc01` (not `monsoon`).
2. **Point at repo root** — OpenCode must see `AGENTS.md` at the top level.
3. **Model** — DeepSeek via OpenCode Desktop (or your paid API if Zen/balance is fixed).
4. **Paste the full brief** — from `## Guardrails` through acceptance criteria (see `docs/handoff/oc-*.md`).
5. **Tell OpenCode:** "Follow `AGENTS.md`. Do not commit or push."
6. **After run:** `git status` and `git diff` in that worktree; paste summary back to Cursor if needed.

### Avoiding Cursor ↔ OpenCode crashes

| Risk | Mitigation |
|------|------------|
| Same file edited twice | Exclusive file lists in briefs + `STATUS.md` locks |
| IDE file watcher conflicts | Separate worktree folders |
| Lost changes | Git only — no "state" only in chat context |
| Merge conflicts | Strict merge order; OC-03 last |
| pytest env | Run tests from integrator folder after each merge |
| `.env` overwritten | Both tools: never edit `.env`; use `.env.example` only |

---

## Today's tracks (LLM Phase A)

| ID | Brief | Owner | Exclusive files |
|----|-------|-------|-----------------|
| OC-01 | `docs/handoff/oc-01-context-slice.md` | OpenCode | `app/services/context_slice.py`, `app/schemas/context.py`, `tests/test_context_slice.py` |
| OC-02 | `docs/handoff/oc-02-ollama-contributions.md` | OpenCode | `app/integrations/ollama/client.py`, `tests/test_ollama_contributions.py` |
| OC-03 | `docs/handoff/oc-03-capture-reflect-digest.md` | OpenCode | `app/services/parser.py`, `app/services/capture_service.py`, `app/schemas/capture.py`, `tests/test_capture_llm.py` |
| CUR-01 | Integration + docs | Cursor | `docs/llm-integration.md`, `dev-docs.md`, `CHANGELOG.md`, `BREADCRUMBS.md`, `handover.md` |

**You (operator):** WA backfill pilot on notcoolio — independent of code tracks.

---

## Session documentation (mandatory when merging)

After each merge into `feature/llm-phase-a`:

- [ ] `CHANGELOG.md` — Added/Changed under Unreleased
- [ ] `docs/llm-integration.md` — match implemented behavior
- [ ] `dev-docs.md` — new ADR row if pattern established
- [ ] `docs/handoff/STATUS.md` — mark track done
- [ ] `BREADCRUMBS.md` + `handover.md` at session end

---

## Offload criteria (when to use OpenCode vs Cursor)

Use OpenCode only when **all** hold:

1. **Heavy** — substantial code + tests
2. **Specifiable** — brief with acceptance criteria exists
3. **Verifiable** — `pytest` / `git diff` / grep probes
4. **Non-sensitive** — no secrets, no production deploy actions

Keep in Cursor: architecture choices, security, merge conflict resolution, final review, Portainer/notcoolio ops.
