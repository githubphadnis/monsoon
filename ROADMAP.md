# Roadmap — monsoon

**North star:** Personal **context atlas** for Prakalp — tasks, email, WhatsApp history,
and Ollama-backed intelligence to help you do better. Not task-only.

See [`docs/context-atlas.md`](./docs/context-atlas.md) for the layer model.

---

## Done (2026-07-07)

- [x] Phase 1 — WAHA webhook capture, Postgres tasks, replies
- [x] Self-chat loop guard, keyword aliases, Portainer sidecar networking
- [x] psycopg3 driver fix + CI smoke tests
- [x] Deploy on notcoolio — sidecar networking, session `prakalp`, capture validated
- [x] Deploy fixes: DNS, psycopg3, empty Gmail env, backfill API params, NOWEB store

---

## Priority 1 — Postgres cleanup (immediate)

- [x] `infra/scripts/cleanup_loop_tasks.py` (dry-run / apply)
- [x] `infra/scripts/cleanup_postgres.sql`
- [ ] Operator runs cleanup on notcoolio after loop incident (if needed)
- [ ] Confirm sane task list for daily use

---

## Priority 2 — Gmail ingestion (after WA pilot)

- [x] Tables: `email_threads`, `email_messages`, `email_participants`
- [x] `app/integrations/gmail/` — client, parse, sync service
- [x] `infra/scripts/gmail_sync.py` + `gmail_oauth_setup.py`
- [x] `/health/gmail-index`
- [ ] Operator: OAuth refresh token in Portainer + first sync
- [ ] LLM classify: action / FYI / waiting (phase 2b)
- [ ] Scheduled incremental sync (cron)

---

## Priority 3 — WhatsApp full history index

- [x] Tables: `wa_chats`, `wa_messages`, `wa_contacts`, `extracted_entities`, `sync_state`
- [x] WAHA client: list chats, paginate messages
- [x] `infra/scripts/wa_backfill.py` + `/health/wa-index`
- [x] Regex entity extract (phone, email, url)
- [x] NOWEB store + correct chat sort params (deploy fix)
- [ ] Operator pilot: `--max-chats 5` on notcoolio (after redeploy)
- [ ] Volume hardening before `--full` (batch commits, caps, skip groups)
- [ ] Ollama 5W1H batch extract (phase 3b)
- [ ] Nightly delta sync job

---

## Priority 4 — Daily use (parallel)

- [ ] Operator runs capture workflow (`todo`, `list`, `digest`, `done`)
- [ ] WorkFlowy mirror (was V1 Phase 2) — when capture stable
- [ ] Reminders + morning digest on real corpus
- [ ] Soul prompt tuning on lenai

---

## V1.0 carry-over (reordered)

### WorkFlowy mirror (fractal context)

See [`docs/workflowy-mirror.md`](./workflowy-mirror.md).

- Task = todo node under bucket; `workflowy_node_id` on `tasks`
- System children: `id: T{n}`, `source`, `due`, `status`
- **Follow-ups / context** = child bullets under task node (human + monsoon)
- `task_context_items` table + push on `note 18 …` / linked captures
- v1.2: reverse sync WF children → Postgres for LLM context slice

### Reminders

- `due_at` / `remind_at` → WAHA outbound
- `snooze` command

### Digest + ops

- Cross-source digest (tasks + email + WA highlights)
- `/health/ready`, structured logs

---

## V1.1+

- pgvector on messages/tasks for semantic recall
- Weekly reflection over full atlas
- Relation hints (duplicate / competing commitments)
- Email → task promotion command

---

## Explicitly out of scope

- OpenLoomi codebase import (ideas only)
- Multi-user / SaaS
- WhatsApp Business API migration
- Full mobile app
