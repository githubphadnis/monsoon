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

| Stage | Input | LLM output | Action |
|-------|-------|------------|--------|
| **Parse** | Free-text WhatsApp | `{ title, due_at?, priority?, tags? }` | Create/update task |
| **Classify** | New task + recent context | `{ bucket: inbox\|today\|waiting\|scheduled }` | Route in WorkFlowy |
| **Enrich digest** | Today's tasks + patterns | Natural-language summary + 1–2 proactive suggestions | `digest` reply |
| **Nudge** | Overdue / stale waiting | Short reminder copy | Outbound WhatsApp |
| **Reflect** | Weekly task_events | Patterns ("you defer X often") | Optional weekly note |

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
