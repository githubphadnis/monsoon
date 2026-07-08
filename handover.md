# Handover — monsoon

## Last worked on

2026-07-08 — Gmail pilot fixed on notcoolio; background sync loops + WorkFlowy reverse sync implemented locally.

## Current state / WIP

- **Deployed on notcoolio** — Gmail pilot succeeded after dedupe fix (`100` messages, `85` threads, `87` participants`).
- **WA pilot:** 5 chats, 91 messages indexed (`prakalp` session).
- **LLM:** `digest`, `reflect`, WorkFlowy push mirror operational; email is in context slice on `main`.
- **Local WIP (not yet pushed):** background scheduler loops (`/health/scheduler`), WA chat cursor batching, WorkFlowy reverse sync, task-context section in context slice.
- **GitHub:** milestones V1.0 / V1.1; issues [#1–#8](https://github.com/githubphadnis/monsoon/issues).

## Next immediate steps

1. **If shipping current local batch:** commit/push, redeploy, then check `/health/scheduler`.
2. **Operator:** let background Gmail / WA loops trickle and watch counts.
3. **Next code:** MS-04 reminder scheduler.

## Environment

| Host | Role |
|------|------|
| `notcoolio` | Docker / Portainer — monsoon stack |
| `lenai` | Ollama (`OLLAMA_BASE_URL` — prefer LAN IP `192.168.1.235:11434`) |

**Portainer essentials:** existing WAHA vars + optional `WORKFLOWY_*`, `OLLAMA_*`. For Gmail add `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN`.
