# Handover — monsoon

## Last worked on

2026-07-10 — family 1:1: inbound LID fix + ignore from_me in peer chats; assistant UX polish.

## Current state / WIP

- **Robot:** Gmail + WA background indexing; WorkFlowy push + reverse; reminders.
- **LLM:** digest / reflect / **ask** share context slice (no entities).
- **Family:** son can use existing 1:1 if both allowlists set; see `docs/family-chat.md`.

## Operator priorities

1. Commit/push LID + from_me_peer fix; redeploy.
2. Confirm Portainer `ALLOWED_WHATSAPP_*` includes son phone + `…@c.us`.
3. Smoke: son `help` in 1:1; check `docker logs monsoon-app` for `Processing capture`.
4. You keep Message yourself for your own monsoon.

## Next product work

- WAHA ephemeral delete of bot replies (optional)
- MS-08 snooze
- Auto-link / active task (MS-06/07)
- Morning outbound digest

## Environment

| Host | Role |
|------|------|
| `notcoolio` | monsoon Portainer stack |
| `lenai` | Ollama (`OLLAMA_BASE_URL` LAN IP preferred) |

**Gmail:** all of Client ID/Secret/Refresh Token; **no** sync label for All Mail.
