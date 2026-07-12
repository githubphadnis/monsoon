# monsoon — project manifest

## Purpose

**monsoon** is a self-hosted **Personal Capture & Reminder** system with an **Ollama
(LLM) brain**. Capture tasks and notes from WhatsApp, persist them reliably, mirror
them into WorkFlowy for human review, and use a local LLM to understand intent,
patterns, and context — then contribute back via reminders, digests, and proactive
nudges.

## Target user

Family operators (Prakalp, Rashmi, Prathamesh) — personal + shared WhatsApp spaces.
Not multi-tenant SaaS; small allowlisted household on one WAHA session.
See `docs/family-model.md`.

## Business value

- Low-friction capture where messages already arrive (WhatsApp).
- Durable local state without depending on a brittle all-in-one assistant platform.
- Human-readable **fractal** task tree in WorkFlowy (task = node, context = children)
- Predictable reminders and daily digests.

## V1 scope (initial boundary)

### Included

- WhatsApp capture via [WAHA](https://waha.devlike.pro/) webhook
- Ollama (lenai) for parse, classify, digest copy, and proactive nudges — see
  [`docs/llm-integration.md`](./docs/llm-integration.md)
- Command grammar (`todo`, `done`, `list`, `snooze`, `digest`, `help`) with LLM
  fallback for free-text capture
- Local Postgres as canonical store (tasks, inbound/outbound messages, sync state)
- WorkFlowy push sync — task todo nodes + context as child bullets (see `docs/workflowy-mirror.md`)
- Reminder scheduler (due/remind_at → WhatsApp outbound)
- Morning digest (scheduled + `digest now`)
- Health endpoints and structured logging
- Docker Compose deployment on `notcoolio`
- Family personal lists + shared group (`docs/family-model.md`)
- `@alias` task assignment; `delete <id>` soft-delete

### Explicitly excluded (deferred)

- Reverse sync from WorkFlowy edits — v1.2+
- Rich web UI — v1.2+ (admin/status only in v1)
- Multi-tenant SaaS / public RBAC — out of scope
- Per-person Message yourself via multi-WAHA sessions — MS-09
- OpenLoomi replacement / unified assistant — separate effort
- Full autonomous agent with tool-use loops — defer; monsoon suggests and nudges first

### In progress (context atlas — beyond original V1 boundary)

- Gmail ingestion (code shipped; operator OAuth + sync pending) — `docs/gmail-ingestion.md`
- WhatsApp full history index (pilot on notcoolio) — `docs/whatsapp-backfill.md`

## Success criteria (V1)

1. Send `todo call bank tomorrow 10am` on WhatsApp → task stored, WorkFlowy bullet created, confirmation reply received.
2. Reminder fires at scheduled time on WhatsApp.
3. `done <id>` completes task locally and syncs to WorkFlowy `Done`.
4. `digest now` returns today's tasks summary.
5. System survives container restart without duplicate reminders (idempotency).
6. Deployed on `notcoolio` with documented env and health checks.

## Integrations

| System | Role | Docs |
|--------|------|------|
| WorkFlowy | Human task outline | [API reference](https://beta.workflowy.com/api-reference/) |
| WAHA | WhatsApp HTTP API | [WAHA docs](https://waha.devlike.pro/) |
| Postgres | Canonical state | — |
| Ollama (lenai) | Parse, enrich, digest, nudges | `docs/llm-integration.md` |
| Gmail (optional) | Email index for context atlas | `docs/gmail-ingestion.md` |

## Getting started

See [README.md](./README.md).
