# Roadmap — monsoon

**North star:** Personal **context atlas** for Prakalp — tasks, email, WhatsApp history,
and Ollama-backed intelligence to help you do better. Not task-only.

See [`docs/context-atlas.md`](./docs/context-atlas.md) for the layer model.

**GitHub issues:** [`docs/roadmap_issues.csv`](./docs/roadmap_issues.csv) (MS-01 …) — import via [`docs/ISSUE_IMPORT.md`](./docs/ISSUE_IMPORT.md).

---

## Agreed build sequence (2026-07-08)

| Order | Issue | Theme | Status |
|-------|-------|-------|--------|
| 1 | [**#1** MS-01](https://github.com/githubphadnis/monsoon/issues/1) | Gmail ingestion — OAuth, sync, email in context slice | **Done (pilot + All Mail resume)** |
| 2 | [**#2** MS-02](https://github.com/githubphadnis/monsoon/issues/2) | WorkFlowy reverse sync (WF children → Postgres) | **Done** |
| 3 | [**#3** MS-03](https://github.com/githubphadnis/monsoon/issues/3) | Scheduled background jobs (Gmail + WA + WF) | **Done** |
| 4 | [**#4** MS-04](https://github.com/githubphadnis/monsoon/issues/4) | Reminder scheduler (`remind_at` → WhatsApp) | **Done** |
| 5 | [**#5** MS-05](https://github.com/githubphadnis/monsoon/issues/5) | Context slice v2 — `task_context_items` in bundle | **Done** (with MS-02) |
| 6 | [**#6** MS-06](https://github.com/githubphadnis/monsoon/issues/6) | Auto-link ambient research → open tasks | V1.1 |
| 7 | [**#7** MS-07](https://github.com/githubphadnis/monsoon/issues/7) | Active task (`on <id>`) | V1.1 |
| 8 | [**#8** MS-08](https://github.com/githubphadnis/monsoon/issues/8) | Snooze / reschedule | Backlog |

---

## Done

- [x] Phase 1 — WAHA webhook capture, Postgres tasks, replies
- [x] Deploy on notcoolio — session `prakalp`, WA + Gmail pilots
- [x] LLM Phase A — context slice, `digest`, `reflect`, title-first replies, tightened digest prompt
- [x] WorkFlowy push + reverse mirror; task context in LLM bundle
- [x] Background sync loops (Gmail/WA/WF) + `/health/scheduler`
- [x] Reminder delivery (`remind_at` → WAHA; clear after send)

---

## Operator catch-up (same day)

- Leave `GMAIL_SYNC_LABEL` **empty** for All Mail (Archive included)
- Optional `GMAIL_INCLUDE_SPAM_TRASH=true`
- Defaults: Gmail every 5 min × 5 pages; WA every 5 min × 5 chats
- Watch `/health/gmail-index` and `/health/wa-index` until counts stabilizeSkirt

---

## Still open / V1.1

- MS-08 snooze command
- Auto-link research to open tasks; active task mode
- Morning digest cron (outbound)
- Email LLM classify / promote-to-task
- pgvector semantic recall

---

## Explicitly out of scope

- OpenLoomi codebase import (ideas only)
- Multi-user / SaaS
- Second capture channel until V1.0 stable
- Full mobile app
