# Handover — monsoon

## Last worked on

2026-07-12 — ephemeral WA cleanup; personal channels docs; Ollama Auto routing; digest isolation.

## Current state / WIP

- **Robot:** Gmail + WA background indexing; WorkFlowy; reminders; **ephemeral delete** (default 5 min).
- **LLM:** digest / reflect / ask; optional `OLLAMA_MODEL_PARSE` + `OLLAMA_MODEL_CHAT`.
- **Family:** personal digests per user; shared family via `MONSOON_SHARED_CHAT_IDS`.
  See `docs/family-chat.md` — wife/son use **1:1 with monsoon number**, not Message yourself.

## Operator priorities

1. Redeploy `main`; confirm ephemeral in `/health/ready`.
2. Allowlist wife/son `<digits>@c.us` + numbers; they message the monsoon WhatsApp.
3. Optional: pull chat model on lenai + set `OLLAMA_MODEL_CHAT`.
4. Smoke: wife `help` in 1:1 → reply → disappears ~5 min later.

## Next product work

- Group RAG (restaurant / lunch opinions)
- MS-08 snooze
- Auto-link / active task (MS-06/07)
- Morning outbound digest

## Environment

| Host | Role |
|------|------|
| `notcoolio` | monsoon Portainer stack |
| `lenai` | Ollama (`OLLAMA_BASE_URL` LAN IP preferred) |
