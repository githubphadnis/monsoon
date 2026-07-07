# Roadmap — monsoon

**North star:** Personal **context atlas** for Prakalp — tasks, email, WhatsApp history,
and Ollama-backed intelligence to help you do better. Not task-only.

See [`docs/context-atlas.md`](./docs/context-atlas.md) for the layer model.

---

## Done (2026-07-07)

- [x] Phase 1 — WAHA webhook capture, Postgres tasks, replies
- [x] Self-chat loop guard, keyword aliases, Portainer sidecar networking
- [x] psycopg3 driver fix + CI smoke tests
- [x] Deploy on notcoolio (operator validating)

---

## Priority 1 — Postgres cleanup (immediate)

- [x] `infra/scripts/cleanup_loop_tasks.py` (dry-run / apply)
- [x] `infra/scripts/cleanup_postgres.sql`
- [ ] Operator runs cleanup on notcoolio after loop incident
- [ ] Confirm sane task list for daily use

---

## Priority 2 — Gmail ingestion

- [ ] Google Cloud project + OAuth credentials
- [ ] Tables: `email_threads`, `email_messages`, `email_participants`
- [ ] `app/integrations/gmail/` — client, sync job, dedupe
- [ ] Env: `GMAIL_*` in Portainer
- [ ] Incremental sync (5–15 min poll)
- [ ] LLM classify: action / FYI / waiting (phase 2b)

---

## Priority 3 — WhatsApp full history index

- [ ] Tables: `wa_chats`, `wa_messages`, `wa_contacts`, `extracted_entities`
- [ ] WAHA backfill job: list chats → paginate all messages
- [ ] Contact derivation (JID, phone, display name)
- [ ] Ollama batch extract: 5W1H + phones + action items
- [ ] Checkpoint cursors in `sync_state`
- [ ] Nightly delta sync

---

## Priority 4 — Daily use (parallel)

- [ ] Operator runs capture workflow (`todo`, `list`, `digest`, `done`)
- [ ] WorkFlowy mirror (was V1 Phase 2) — when capture stable
- [ ] Reminders + morning digest on real corpus
- [ ] Soul prompt tuning on lenai

---

## V1.0 carry-over (reordered)

### WorkFlowy mirror

- Create/update bullets via WorkFlowy API
- `workflowy_node_id` on tasks
- `done <id>` → complete + sync

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
