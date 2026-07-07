# Developer documentation — monsoon

## Architectural decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-07-07 | Postgres as source of truth; WorkFlowy as mirror | Avoid WorkFlowy API rate limits and ambiguous reverse-sync; local DB owns reminders/idempotency |
| 2026-07-07 | WAHA for WhatsApp | Self-hosted HTTP API + webhooks; fits Docker on notcoolio |
| 2026-07-07 | Deterministic command grammar in v1 | Reliable capture before optional Ollama NL parsing |
| 2026-07-07 | Ollama as core LLM layer (lenai) | Parse, classify, digest, and nudges; borrow OpenLoomi insight/soul patterns at smaller scope |
| 2026-07-07 | Core governance tier | Solo personal tool; promote to Governed if collaborators join |

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

- `users` — operator profile, timezone, WorkFlowy root id
- `inbound_messages` — webhook audit + dedupe
- `tasks` — canonical tasks
- `task_events` — immutable history
- `outbound_messages` — delivery audit
- `sync_state` — WorkFlowy node mapping

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
