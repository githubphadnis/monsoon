# Handover — monsoon

## Last worked on

2026-07-07 — deploy hardening + WA backfill pilot debugging on notcoolio.

## Current state / WIP

- **Deployed on notcoolio** via Portainer (`docker-compose.portainer.yml`) @ `dac7ce6`.
- **WA pilot SUCCESS:** 5 chats, 91 messages, 12 contacts, 7 entities (`--max-chats 5`).
- **LLM Phase A on main:** context slice, `digest`, `reflect`, WorkFlowy push mirror.
- **WAHA:** session `prakalp`, NOWEB store enabled, webhook ok.

## Next immediate steps

1. WhatsApp smoke: `digest`, `reflect <topic>`, `todo smoke test`.
2. Optional: WorkFlowy env in Portainer (`WORKFLOWY_API_KEY`, `WORKFLOWY_ROOT_NODE_ID`).
3. Defer full backfill until volume hardening.

## Environment

| Host | Role |
|------|------|
| `notcoolio` | Docker / Portainer — monsoon stack (`monsoon-app`, `monsoon-waha`, `monsoon-postgres`) |
| `lenai` | Ollama (`OLLAMA_BASE_URL`) |

**Portainer essentials:** `POSTGRES_PASSWORD`, `WAHA_API_KEY`, `WAHA_DASHBOARD_PASSWORD`, `WHATSAPP_SWAGGER_PASSWORD`, `ALLOWED_WHATSAPP_NUMBERS`, `WAHA_SESSION=prakalp`, `MONSOON_ALLOW_SELF_CHAT=true`. Omit `GMAIL_SYNC_MAX_PAGES` or leave unset until Gmail pilot.

**SSH tunnel for WAHA dashboard:** `ssh -L 13000:127.0.0.1:13000 prakalp@notcoolio` → `http://127.0.0.1:13000/dashboard`
