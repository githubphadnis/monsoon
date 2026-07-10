# LLM integration (Ollama) — monsoon

Ollama on **lenai** is a **core** part of monsoon — not an optional add-on. The system
should understand tasks, notice patterns, and contribute back proactively (digests,
nudges, clarifications), not only parse rigid commands.

## Design principles

1. **Deterministic shell, intelligent core** — WhatsApp commands and Postgres remain
   reliable; the LLM enriches parsing, classification, and outbound text.
2. **Structured outputs** — LLM returns JSON schemas (task fields, priority, due
   inference, follow-up suggestions) validated before persistence.
3. **Borrow proven patterns** — insight pipeline and soul-prompt ideas from
   [OpenLoomi](https://github.com/openloomi/openloomi) (message → enrich → act),
   adapted to monsoon's smaller scope.
4. **Fail open** — if Ollama is unreachable, fall back to regex/command grammar;
   never block capture.

## Ollama connection

| Setting | Example |
|---------|---------|
| `OLLAMA_BASE_URL` | `http://lenai:11434` (Tailscale/LAN) |
| `OLLAMA_MODEL` | `llama3.2` or your default on lenai |
| `OLLAMA_TIMEOUT_SECONDS` | `60` |

Use HTTP API: `POST /api/chat` or `/api/generate` with JSON response format when
the model supports it.

## LLM responsibilities (V1 → V1.1)

| Stage | Status | Input | LLM output | Action |
|-------|--------|-------|------------|--------|
| **Parse** | Shipped | Free-text WhatsApp | JSON task fields | Create task (regex first; Ollama only for clear commands) |
| **Ask** | Shipped | Question / free text + context slice | Prose answer | Conversational reply (not a new todo) |
| **Context slice** | Shipped | Postgres tasks + WA index (+ email) | SQL bundle text | Feed digest / reflect / ask |
| **Enrich digest** | Shipped | Context slice (no entities) | Action digest prose | `digest` / `summary` (SQL fallback if Ollama down / bad dump) |
| **Reflect** | Shipped | Topic + context slice | Active/blockers/next step | `reflect <topic>` |
| **Classify** | Planned | New task + context | bucket routing | WorkFlowy bucket move |
| **Nudge** | Shipped | Overdue / due remind_at | Short reminder | Background ReminderService |
| **Weekly reflect** | Planned | task_events | Patterns | Cron |

## Context slice (shipped 2026-07-08)

`app/services/context_slice.py` — OpenLoomi-inspired **SQL bundle, not graph DB**:

- Open tasks (up to 20)
- Task context (`task_context_items`, up to 30)
- Recent email messages (up to 20, topic-filtered when requested)
- Recent WA messages (up to 30, topic-filtered when requested)
- Extracted entities (phones, emails, URLs)
- Char budget default 12k — truncates oldest first

Used by `digest` and `reflect` before every Ollama call.

## WhatsApp commands (LLM)

| Command | Behavior |
|---------|----------|
| `digest` / `summary` | Ollama soul + context slice (tasks/email/WA, **no entity dump**) → prose action digest; SQL fallback |
| `reflect griham` | Topic-filtered slice → reflection on what's active |
| Free-text questions | `ask` path — Ollama answers using the same context slice |
| Explicit `todo` / `remind` / `note` | Create tasks (regex or high-confidence parse) |

### Context awareness (status)

**Now:** digest / reflect / ask all share the Postgres context slice (open tasks, task notes, recent email + WA). Entity lists are stored but **not** fed into LLM prompts (they caused phone/email dumps). Bot outbound is filtered out of WA lines.

**Later:** auto-link free text to an active task (MS-06/07), morning outbound digest, optional ephemeral delete of bot messages.

### Deferred UX ideas

- Auto-delete monsoon WhatsApp replies after ~5 minutes (needs WAHA delete API spike).
- Dedicated monitored chats with TTL — prefer fixing reply quality first.

## WorkFlowy integration (shipped 2026-07-08)

Push sync when `WORKFLOWY_API_KEY` set and `WORKFLOWY_ENABLED=true`:

- Task create → todo node under bucket + system children (`id: T{n}`, `source`, `due`, `status`)
- `note <id> <text>` → context child in WF + `task_context_items` row
- `done <id>` → complete WF todo node

See [`docs/workflowy-mirror.md`](./workflowy-mirror.md). Reverse sync (WF → Postgres) remains v1.2.

## Soul prompt (personality)

Inspired by OpenLoomi's `ai_soul_prompt` / soul presets — one operator-editable
system prompt stored in DB or env (`MONSOON_SOUL_PROMPT`). Default tone: concise,
practical, slightly proactive; no corporate filler.

Example preset themes (future UI):
- **Executor** — action-first, minimal prose
- **Strategist** — connects tasks to bigger goals
- **Calm** — low-pressure nudges

## Pipeline sketch

```text
WhatsApp text
    → inbound_messages (audit)
    → [optional] LLM parse (Ollama)
    → tasks + task_events
    → WorkFlowy mirror
    → [scheduled] LLM digest / nudge
    → WAHA sendText
```

## What we are not copying from OpenLoomi

- Importing OpenLoomi packages wholesale (Next.js app, connectors monolith)
- Guest accounts / heavy web UI
- Baileys-in-app WhatsApp (we use WAHA)

We **do** grow toward the same north star: multi-source personal context atlas.
See [`docs/context-atlas.md`](./context-atlas.md).

## References

- OpenLoomi insight processor: `apps/web/lib/insights/processor.ts`
- OpenLoomi soul presets: `packages/shared/src/soul.ts`
- Ollama API: https://github.com/ollama/ollama/blob/main/docs/api.md
