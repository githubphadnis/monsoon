# Handover — monsoon

## Last worked on

2026-07-07

## Current state / WIP

- **Deployed on notcoolio** via Portainer — WAHA paired session `prakalp`, WORKING.
- User sees Event Monitor updates but **no WhatsApp replies** after fixing `WAHA_SESSION`.
- Likely cause: webhook URL still `http://app:8080` (WAHA cannot resolve `app`) — inbound never reaches monsoon.

## Broken things

- WhatsApp capture loop: no reply despite messages in WAHA Event Monitor.
- Diagnose on notcoolio: `curl http://127.0.0.1:8080/health/webhook` and `docker logs monsoon-app`.

## Next immediate steps

1. Push latest `main` → Portainer pull & redeploy (app image `pull_policy: always`).
2. Confirm `health/webhook` shows `"configured": true` and URL contains `monsoon-app`.
3. `bash infra/scripts/diagnose_stack.sh` on notcoolio if still broken.
4. WhatsApp: `todo test monsoon reply`.

## Environment

| Host | Role |
|------|------|
| `notcoolio` | Docker / Portainer — monsoon stack |
| `lenai` | Ollama (optional) |
