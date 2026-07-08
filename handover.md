# Handover — monsoon

## Last worked on

2026-07-07 — deploy hardening + WA backfill pilot debugging on notcoolio.

## Current state / WIP

- **Deployed on notcoolio** via Portainer (`docker-compose.portainer.yml`).
- **WAHA:** dedicated monsoon instance, NOWEB engine, session **`prakalp`**, sidecar networking (`network_mode: service:app`).
- **App:** FastAPI + Postgres; webhook auto-config + reconciler; capture + replies working when session/env aligned.
- **Shipped in code (operator validating):** WA index backfill, Gmail sync, Postgres cleanup scripts, outbound echo guard, keyword aliases.
- **WA backfill pilot:** hit `400` on `list_chats` (wrong `sortBy`) — **fixed on `main`**; operator needs redeploy + retry `--max-chats 5`.

## Broken / watch

| Item | Status |
|------|--------|
| WAHA `EAI_AGAIN web.whatsapp.com` | Fixed in compose (explicit DNS on `app`); redeploy if recurs |
| App crash `gmail_sync_max_pages ''` | Fixed — empty optional int treated as unset |
| `list_chats` 400 | Fixed — use `conversationTimestamp`; enable NOWEB store on session |
| Full WA backfill on huge groups | **Not hardened** — pilot only until batch commits / caps / skip-groups |

## Next immediate steps

1. **Parallel LLM Phase A** — see `docs/parallel-work.md` + `docs/handoff/STATUS.md`.
2. Operator: WA backfill `--max-chats 5` (independent).
3. After OC merges: deploy `feature/llm-phase-a` to notcoolio when reviewed.

## Environment

| Host | Role |
|------|------|
| `notcoolio` | Docker / Portainer — monsoon stack (`monsoon-app`, `monsoon-waha`, `monsoon-postgres`) |
| `lenai` | Ollama (`OLLAMA_BASE_URL`) |

**Portainer essentials:** `POSTGRES_PASSWORD`, `WAHA_API_KEY`, `WAHA_DASHBOARD_PASSWORD`, `WHATSAPP_SWAGGER_PASSWORD`, `ALLOWED_WHATSAPP_NUMBERS`, `WAHA_SESSION=prakalp`, `MONSOON_ALLOW_SELF_CHAT=true`. Omit `GMAIL_SYNC_MAX_PAGES` or leave unset until Gmail pilot.

**SSH tunnel for WAHA dashboard:** `ssh -L 13000:127.0.0.1:13000 prakalp@notcoolio` → `http://127.0.0.1:13000/dashboard`
