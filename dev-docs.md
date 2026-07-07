# Developer documentation — monsoon

## Architectural decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-07-07 | Postgres as source of truth; WorkFlowy as mirror | Avoid WorkFlowy API rate limits and ambiguous reverse-sync; local DB owns reminders/idempotency |
| 2026-07-07 | WAHA for WhatsApp | Self-hosted HTTP API + webhooks; fits Docker on notcoolio |
| 2026-07-07 | Deterministic command grammar in v1 | Reliable capture before optional Ollama NL parsing |
| 2026-07-07 | Ollama as core LLM layer (lenai) | Parse, classify, digest, and nudges; borrow OpenLoomi insight/soul patterns at smaller scope |
| 2026-07-07 | Context atlas north star | Tasks are one lens; Gmail + full WA index + Ollama intelligence — see `docs/context-atlas.md` |

## WorkFlowy folder structure (canonical)

```text
Personal Capture & Reminder
├── Inbox
├── Today
├── Next
├── Waiting
├── Scheduled
├── Done
├── Reference
└── Daily Digests
```

Child metadata bullets under each task (preferred over tag-stuffed titles):

- `id: T18`
- `source: whatsapp`
- `due: 2026-07-08 10:00`
- `status: scheduled`

## Data model (summary)

**Today**

- `users` — operator profile, timezone, WorkFlowy root id
- `inbound_messages` — webhook audit + dedupe
- `tasks` — canonical tasks
- `task_events` — immutable history
- `outbound_messages` — delivery audit

**Planned (context atlas)**

- `email_threads`, `email_messages`, `email_participants`
- `wa_chats`, `wa_messages`, `wa_contacts`
- `extracted_entities` — 5W1H / phones / facts from messages
- `contacts` — unified people across WA + email
- `sync_state` — cursors for Gmail + WA backfill + WorkFlowy

## Errors faced & solutions

| Date | Error | Solution |
|------|-------|----------|
| — | — | — |

## Patterns to avoid

- Making WorkFlowy the system of record — breaks reminder/idempotency semantics.
- Parsing free-form NL in v1 without fallback — use explicit commands first.
- Skipping idempotency on webhooks — WAHA may deliver duplicates.

## Successful patterns

- cOcO scaffold from day one — manifest, roadmap, and handover before code sprawl.
