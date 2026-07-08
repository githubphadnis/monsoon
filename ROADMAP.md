# Roadmap — monsoon

**North star:** Personal **context atlas** for Prakalp — tasks, email, WhatsApp history,
and Ollama-backed intelligence to help you do better. Not task-only.

See [`docs/context-atlas.md`](./docs/context-atlas.md) for the layer model.

**GitHub issues:** [`docs/roadmap_issues.csv`](./docs/roadmap_issues.csv) (MS-01 …) — import via [`docs/ISSUE_IMPORT.md`](./docs/ISSUE_IMPORT.md).

---

## Agreed build sequence (2026-07-08)

| Order | Issue | Theme | Status |
|-------|-------|-------|--------|
| 1 | [**#1** MS-01](https://github.com/githubphadnis/monsoon/issues/1) | Gmail ingestion — OAuth, sync, email in context slice | **In progress** |
| 2 | [**#2** MS-02](https://github.com/githubphadnis/monsoon/issues/2) | WorkFlowy reverse sync (WF children → Postgres) | Backlog |
| 3 | [**#3** MS-03](https://github.com/githubphadnis/monsoon/issues/3) | Scheduled background jobs (Gmail + WA delta + digest cron) | Backlog |
| 4 | [**#4** MS-04](https://github.com/githubphadnis/monsoon/issues/4) | Reminder scheduler (`remind_at` → WhatsApp) | Backlog |
| 5 | [**#5** MS-05](https://github.com/githubphadnis/monsoon/issues/5) | Context slice v2 — `task_context_items` in bundle | Backlog |
| 6 | [**#6** MS-06](https://github.com/githubphadnis/monsoon/issues/6) | Auto-link ambient research → open tasks | V1.1 |
| 7 | [**#7** MS-07](https://github.com/githubphadnis/monsoon/issues/7) | Active task (`on <id>`) | V1.1 |
| 8 | [**#8** MS-08](https://github.com/githubphadnis/monsoon/issues/8) | Snooze / reschedule | Backlog |

---

## Done

- [x] Phase 1 — WAHA webhook capture, Postgres tasks, replies
- [x] Self-chat loop guard, keyword aliases, Portainer sidecar networking
- [x] Deploy on notcoolio — session `prakalp`, WA pilot (5 chats, 91 msgs)
- [x] LLM Phase A — context slice, `digest`, `reflect`, title-first replies
- [x] WorkFlowy push mirror — create, `note <id>`, `done`
- [x] Gmail tables + sync service + OAuth script + `/health/gmail-index`
- [x] WA backfill pilot + entity extract

---

## MS-01 — Gmail ingestion (now)

- [x] Tables: `email_threads`, `email_messages`, `email_participants`
- [x] `app/integrations/gmail/` — client, parse, sync service
- [x] `infra/scripts/gmail_sync.py` + `gmail_oauth_setup.py`
- [x] `/health/gmail-index`
- [ ] **Operator:** OAuth refresh token in Portainer + first sync on notcoolio
- [x] Email lines in context slice for `digest` / `reflect`
- [ ] LLM classify: action / FYI / waiting (phase 2b — V1.1)

---

## MS-02 — WorkFlowy reverse sync

See [`docs/workflowy-mirror.md`](./docs/workflowy-mirror.md).

- [x] Push: task node + `note <id>` context children
- [ ] Read WF children → `task_context_items` (skip system prefixes)
- [ ] Feed reverse-synced items into context slice (pairs with MS-05)

---

## MS-03 — Scheduled jobs

- [ ] APScheduler in app (Gmail incremental ~15 min)
- [ ] WA delta backfill (nightly, capped until volume hardening)
- [ ] Morning digest cron (optional; after MS-04 pattern)

---

## MS-04 — Reminders

- [ ] `remind_at` / `due_at` → WAHA outbound
- [ ] Idempotent delivery across restarts
- [ ] MS-08: `snooze` command

---

## MS-05 / MS-06 / MS-07 — Context intelligence (V1.0–V1.1)

- [ ] `task_context_items` in LLM context bundle
- [ ] Auto-link free-text / research to best-matching open task
- [ ] `on <id>` active task for multi-step work

---

## V1.1+

- pgvector semantic recall
- Weekly reflection over full atlas
- Email → task promotion command
- Relation hints (duplicate / competing commitments)

---

## Explicitly out of scope

- OpenLoomi codebase import (ideas only)
- Multi-user / SaaS
- Second capture channel (Telegram / HTTP API) until V1.0 stable
- Full mobile app
