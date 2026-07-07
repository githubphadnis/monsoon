# Handover — monsoon

## Last worked on

2026-07-07

## Current state / WIP

- **Deployed on notcoolio** via Portainer (`docker-compose.portainer.yml`) — user reports stack up, Postgres OK.
- GHCR: `ghcr.io/githubphadnis/monsoon:main`.
- Dedicated **monsoon WAHA** on **`127.0.0.1:13000`** — localhost-only; reach via SSH tunnel from PC.
- Phase 1 app code shipped; webhook not yet wired until WAHA paired.

## Broken things

- **WAHA dashboard unreachable from PC** if opening `http://notcoolio:13000` — expected; use SSH tunnel (see `docs/deploy-portainer.md` §3).

## Next immediate steps

1. SSH tunnel + open `http://127.0.0.1:13000/dashboard`; start session **`default`**, scan QR (WAHA Core — no custom session names).
2. Run `configure_waha_webhook.py` (webhook → `http://app:8080/api/webhooks/waha`).
3. WhatsApp capture test (`todo …`).
4. Phase 2: WorkFlowy sync.

## Environment

| Host | Role |
|------|------|
| `notcoolio` | Docker / Portainer — target deploy |
| `lenai` | Ollama (optional, v1.1+) |

## Secrets (do not commit)

- `WORKFLOWY_API_KEY` — https://workflowy.com/api-key
- `WAHA_API_KEY` — from `docker compose run ... init-waha`
- `DATABASE_URL` — Postgres connection string
