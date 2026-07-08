# Developer documentation — monsoon

## Architectural decisions

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-07-07 | Postgres as source of truth; WorkFlowy as mirror | Avoid WorkFlowy API rate limits and ambiguous reverse-sync; local DB owns reminders/idempotency |
| 2026-07-07 | WAHA for WhatsApp | Self-hosted HTTP API + webhooks; fits Docker on notcoolio |
| 2026-07-07 | Deterministic command grammar in v1 | Reliable capture before optional Ollama NL parsing |
| 2026-07-07 | Ollama as core LLM layer (lenai) | Parse, classify, digest, and nudges; borrow OpenLoomi insight/soul patterns at smaller scope |
| 2026-07-07 | WAHA sidecar networking | `network_mode: service:app` — webhooks/API via `127.0.0.1`; avoids Docker DNS between WAHA and app |
| 2026-07-07 | NOWEB store required for history APIs | `/chats` and `/messages` need `config.noweb.store.enabled`; monsoon sets on session PUT at startup |
| 2026-07-07 | Context atlas north star | Tasks are one lens; Gmail + full WA index — see `docs/context-atlas.md` |
| 2026-07-08 | Context slice + LLM digest/reflect | SQL bundle per LLM call; soul prompt on Ollama contributions; fail-open to SQL digest |
| 2026-07-08 | WorkFlowy push mirror v1 | Task create → WF todo + system children; `note <id>` → context child; `task_context_items` table |

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

**Shipped (context atlas)**

- `email_threads`, `email_messages`, `email_participants` — Gmail sync
- `wa_chats`, `wa_messages`, `wa_contacts`
- `extracted_entities` — regex phones/emails/URLs (LLM 5W1H later)
- `sync_state` — reserved for global cursors

**Planned**

- `task_context_items` — follow-up content (mirrored as WF child bullets)
- `contacts` — unified people across WA + email

## Errors faced & solutions

| Date | Error | Solution |
|------|-------|----------|
| 2026-07-07 | WAHA webhook to `app:8080` — no reply | Sidecar `127.0.0.1`; reconciler + `MONSOON_WEBHOOK_TARGET_URL` |
| 2026-07-07 | `ModuleNotFoundError: psycopg2` | Normalize `DATABASE_URL` to `postgresql+psycopg://` |
| 2026-07-07 | Self-chat bot reply loop | `outbound_guard.py` + commit outbound before echo |
| 2026-07-07 | `EAI_AGAIN web.whatsapp.com` | Explicit DNS on `app` in compose (`127.0.0.11`, `1.1.1.1`, `8.8.8.8`) |
| 2026-07-07 | `gmail_sync_max_pages` validation on `''` | Pydantic coerces empty string → `None` |
| 2026-07-07 | `list_chats` 400 Bad Request | `sortBy=conversationTimestamp` (not `messageTimestamp`); enable NOWEB store |

## Patterns to avoid

- Making WorkFlowy the system of record — breaks reminder/idempotency semantics.
- Parsing free-form NL in v1 without fallback — use explicit commands first.
- Skipping idempotency on webhooks — WAHA may deliver duplicates.

## Successful patterns

- cOcO scaffold from day one — manifest, roadmap, and handover before code sprawl.

## Parallel work — Cursor + OpenCode (2026-07-08)

**Decision:** For fast delivery, implementation slices may run in **OpenCode Desktop** while
Cursor stays **orchestrator + reviewer + integrator**. Manual handoff (same model as griham
`dev-docs.md §1.10`).

**Coordination:** `docs/parallel-work.md` (worktrees, merge order, conflict avoidance).
**Lock board:** `docs/handoff/STATUS.md` — update before starting a track.
**Briefs:** `docs/handoff/oc-*.md` — paste-ready prompts; template in `docs/handoff/TEMPLATE.md`.

**Rules:**

1. One agent per exclusive file set; OC-03 after OC-01 + OC-02.
2. Separate git worktrees (`monsoon-oc01`, …) or sequential single-folder runs.
3. OpenCode never commits/pushes; Cursor reviews `git diff` + `pytest` before merge.
4. Every merge updates `CHANGELOG.md`, `docs/llm-integration.md`, and session docs.

**Current initiative:** LLM Phase A — context slice, Ollama contributions, `reflect` + LLM digest.
