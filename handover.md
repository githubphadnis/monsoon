# Handover — monsoon

## Last worked on

2026-07-10 — WhatsApp assistant UX: ask path, digest anti-dump, quieter acks, WorkFlowy notes.

## Current state / WIP

- **Robot:** Gmail + WA background indexing; WorkFlowy push + reverse; reminders.
- **LLM:** digest / reflect / **ask** share context slice (tasks, notes, email, WA — **no entities**).
- **UX:** prose digests; free-text questions answered; short `Saved · #N` acks.

## Operator priorities

1. Redeploy latest `main`.
2. Smoke `digest` + a free-text question + `todo` + `list`.
3. Leave indexes running.

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
