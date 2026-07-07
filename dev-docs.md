# Developer documentation — monsoon

## Architectural decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-07-07 | Postgres as source of truth; WorkFlowy as mirror | Avoid WorkFlowy API rate limits and ambiguous reverse-sync; local DB owns reminders/idempotency |
| 2026-07-07 | WAHA for WhatsApp | Self-hosted HTTP API + webhooks; fits Docker on notcoolio |
| 2026-07-07 | Deterministic command grammar in v1 | Reliable capture before optional Ollama NL parsing |
| 2026-07-07 | Ollama as core LLM layer (lenai) | Parse, classify, digest, and nudges; borrow OpenLoomi insight/soul patterns at smaller scope |
| 2026-07-07 | WorkFlowy fractal context | Task node = todo; follow-ups are child bullets — see `docs/workflowy-mirror.md` |

## WorkFlowy — fractal task + context

Full spec: [`docs/workflowy-mirror.md`](./workflowy-mirror.md).

Each **task** is one todo node under a bucket (`Inbox`, `Today`, …). **Follow-ups,
notes, links, and captured snippets** are **child bullets under that task node** — not
siblings, not stuffed into the title. System metadata (`id: T18`, `due:`, `source:`)
are fixed children; everything else is context you or monsoon add over time.

```text
Today
  └── Call bank                    ← task (todo)
        ├── id: T18                ← system
        ├── due: 2026-07-08 10:00
        └── spoke to agent, ref #44921   ← your follow-up (fractal context)
```

Postgres stores ids and reminders; WorkFlowy is the visual todo list with context.
v1.2 reverse sync reads WF children back into `task_context_items` for the LLM.

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

**Context** (follow-ups, links, WA/email excerpts) = additional child bullets under the
same task node — see `docs/workflowy-mirror.md`.

## Data model (summary)

**Today**

- `users` — operator profile, timezone, WorkFlowy root id
- `inbound_messages` — webhook audit + dedupe
- `tasks` — canonical tasks (`workflowy_node_id` = task bullet)
- `task_events` — immutable history
- `task_context_items` — follow-up content (mirrored as WF child bullets)
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
