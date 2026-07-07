# Roadmap — monsoon

## V0.1.0 — Bootstrap (current)

**Target:** 2026-07-07

- [x] GitHub repo created
- [x] cOcO docs scaffold
- [x] Docker Compose + `.env.example`
- [x] App skeleton + health endpoints
- [ ] First push to `main`
- [ ] Deploy on notcoolio

---

## V1.0 — Personal Capture & Reminder (MVP)

**Target:** ~1–2 weeks focused work

### Phase 1 — Core capture loop (2–3 days)

- WAHA webhook receiver with auth + dedupe
- Parse `todo ...` / `note ...` (regex) + **Ollama parse** for free-text fallback
- Persist task in Postgres
- Reply confirmation on WhatsApp (`Task #N created`)

### Phase 1b — LLM layer (1–2 days, parallel with Phase 2)

- Ollama client (`app/integrations/ollama/`)
- Structured JSON parse: title, due, priority, bucket
- `MONSOON_SOUL_PROMPT` for digest/nudge tone
- See [`docs/llm-integration.md`](./docs/llm-integration.md)

### Phase 2 — WorkFlowy mirror (1–2 days)

- Create/update bullets via WorkFlowy API
- Store `workflowy_node_id` on tasks
- `done <id>` → complete locally + sync to `Done`

### Phase 3 — Reminders (1–2 days)

- `due_at` / `remind_at` scheduling
- Outbound reminder via WAHA
- `snooze` command

### Phase 4 — Digest + ops (1 day)

- `digest now` + morning cron
- `/health/ready` checks DB + WAHA
- Structured logs + outbound audit table

### Phase 5 — Hardening (ongoing)

- Webhook idempotency keys
- Retry/backoff for WorkFlowy sync
- Backup notes for Postgres volume

### V1 success demo

Send `todo buy milk tomorrow 8am` → stored → WorkFlowy bullet → reminder fires → `done 1` completes.

---

## V1.1 — Smarter capture

- Weekly pattern reflection (LLM over `task_events`)
- Soul prompt presets (Executor / Strategist / Calm)
- Simple admin status page

---

## V1.2 — Expand

- Email capture (single inbox)
- WorkFlowy reverse-sync (read-only reconciliation)
- Multi-device operator auth (if needed)

---

## Explicitly out of scope

- OpenLoomi replacement
- Team collaboration / multi-tenant
- WhatsApp Business API migration
- Full mobile app
