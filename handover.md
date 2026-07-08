# Handover — monsoon

## Last worked on

2026-07-08 — Roadmap + GH issues MS-01…08; Gmail email section in context slice (MS-01 partial).

## Current state / WIP

- **Deployed on notcoolio** — redeployed with title-first LLM replies (`c762e3a`).
- **WA pilot:** 5 chats, 91 messages indexed (`prakalp` session).
- **LLM:** `digest`, `reflect`, WorkFlowy push mirror operational.
- **MS-01 Gmail:** sync code shipped; **operator OAuth + first sync not done yet**.
- **GitHub:** milestones V1.0 / V1.1; issues [#1–#8](https://github.com/githubphadnis/monsoon/issues).

## Next immediate steps

1. **Operator — finish MS-01 (#1):** Gmail OAuth in Portainer + pilot sync (see `docs/gmail-ingestion.md`, `BREADCRUMBS.md`).
2. **Code — MS-02 (#2):** WorkFlowy reverse sync.
3. **Code — MS-03 (#3):** APScheduler (Gmail incremental, WA delta).

## Environment

| Host | Role |
|------|------|
| `notcoolio` | Docker / Portainer — monsoon stack |
| `lenai` | Ollama (`OLLAMA_BASE_URL` — prefer LAN IP `192.168.1.235:11434`) |

**Portainer essentials:** existing WAHA vars + optional `WORKFLOWY_*`, `OLLAMA_*`. For Gmail add `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN`.
