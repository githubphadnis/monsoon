# Handover — monsoon

## Last worked on

2026-07-07

## Current state / WIP

- Repo bootstrapped at `C:\projects\monsoon` with cOcO baseline docs.
- GitHub remote: https://github.com/githubphadnis/monsoon (LICENSE only on remote before first push).
- Application: **Phase 1 implemented** — WAHA webhook, task capture, Ollama fallback parse, WhatsApp replies.
- Not yet deployed on notcoolio.

## Broken things

- None (greenfield).

## Next immediate steps

1. Review scaffold docs (`project-manifest.md`, `ROADMAP.md`).
2. Commit and push bootstrap to `main` when ready.
3. Deploy stack on `notcoolio`; pair WAHA session.
4. Implement Phase 1: webhook intake + `todo` → Postgres + WhatsApp confirmation.
5. Implement Phase 2: WorkFlowy push sync.

## Environment

| Host | Role |
|------|------|
| `notcoolio` | Docker / Portainer — target deploy |
| `lenai` | Ollama (optional, v1.1+) |

## Secrets (do not commit)

- `WORKFLOWY_API_KEY` — https://workflowy.com/api-key
- `WAHA_API_KEY` — from `docker compose run ... init-waha`
- `DATABASE_URL` — Postgres connection string
