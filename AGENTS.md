# AGENTS.md — monsoon

Canonical, tool-agnostic entrypoint for agents working on **monsoon** — a personal
capture & reminder system (WorkFlowy + WhatsApp via WAHA + local Postgres).

**Governance tier:** Core

**Repo:** https://github.com/githubphadnis/monsoon

## Read order

`AGENTS.md` → `project-manifest.md` → `README.md` → `dev-docs.md` → `handover.md` → `ROADMAP.md`

## Code truth

- **V1 scope:** Personal Capture & Reminder only — not a full assistant platform.
- **Source of truth:** local Postgres (tasks, reminders, sync state, audit).
- **WorkFlowy:** mirrored human-facing outline (push sync from app; no reverse sync in v1).
- **WhatsApp:** WAHA webhook in, WAHA HTTP API out (capture + confirmations + reminders).
- **Deploy target:** `notcoolio` (mini Lenovo) via Docker Compose / Portainer.
- **Ollama (lenai):** core — parse, classify, digest, and proactive replies; command
  grammar is the fallback when LLM is down. See `docs/llm-integration.md`.

## Dev server

```bash
cp .env.example .env
docker compose up -d
# API (when implemented): http://127.0.0.1:8080/health
```

| URL / check | Purpose |
|-------------|---------|
| `GET /health/live` | Process up |
| `GET /health/ready` | DB + integrations reachable |
| WAHA dashboard | WhatsApp session (localhost only by default) |

## Env essentials

- `DATABASE_URL`, `WORKFLOWY_API_KEY`, `WAHA_BASE_URL`, `WAHA_API_KEY`
- `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `MONSOON_SOUL_PROMPT`
- `APP_TIMEZONE` (e.g. `Europe/Amsterdam`)
- `ALLOWED_WHATSAPP_NUMBERS` (comma-separated E.164 without `+`)

## Session contract

1. Read the docs above before changing anything.
2. Follow [`CODING_GUIDELINES.md`](./CODING_GUIDELINES.md) and [`agent_rules.md`](./agent_rules.md).
3. At session end: update `BREADCRUMBS.md` (always); update `handover.md` / `dev-docs.md` /
   `CHANGELOG.md` when state changed. Do not commit or push unless explicitly asked.

## Canonical artifacts

`project-manifest.md`, `README.md`, `dev-docs.md`, `handover.md`, `BREADCRUMBS.md`,
`ROADMAP.md`, `CHANGELOG.md`.
