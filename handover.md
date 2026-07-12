# Handover — monsoon

## Last worked on

2026-07-12 — MS-09 multi-session WAHA routing.

## Current state / WIP

- **Multi-session:** `MONSOON_WAHA_SESSION_MAP` + optional `MONSOON_WAHA_ENDPOINTS`.
  Replies use inbound webhook session; reminders/ephemeral/backfill follow the map.
- **Family:** `docs/family-model.md`
- **Assign / delete / ephemeral / Ollama Auto** shipped.

## Operator priorities

1. Redeploy; create WAHA sessions + QR Rashmi/Prathamesh phones.
2. Set `MONSOON_WAHA_SESSION_MAP` (and aliases / shared group).
3. Smoke Message yourself per person + family `@assign`.

## Next product work

- MS-10 assign notify + shared done ([#9](https://github.com/githubphadnis/monsoon/issues/9))
- Group RAG / lunch memory
- MS-08 snooze

## Environment

| Host | Role |
|------|------|
| `notcoolio` | monsoon Portainer stack |
| `lenai` | Ollama |
