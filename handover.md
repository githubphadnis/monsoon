# Handover — monsoon

## Last worked on

2026-07-08 — digest prompt harden; reminders; same-day background Gmail/WA indexing.

## Current state / WIP

- **Robot:** Gmail pilot: 100 msgs / 85 threads (incomplete list resume fixed).
- **Background jobs:** Gmail, WA, WorkFlowy reverse, reminder poller — `/health/scheduler`.
- **LLM:** title-first context + tightened digest/reflect instructions.
- **WorkFlowy:** push + reverse sync; task context in LLM bundle.

## Operator priorities

1. Redeploy latest `main`.
2. Clear `GMAIL_SYNC_LABEL` if set to `-INBOX` — leave empty for Archive/All Mail.
3. Leave stack running; watch gmail/wa index counts climb through the day.
4. Retest `digest`.

## Next product work (defer / Griham-compatible pause)

- MS-08 snooze
- Auto-link / active task (MS-06/07)
- Morning outbound digest

## Environment

| Host | Role |
|------|------|
| `notcoolio` | monsoon Portainer stack |
| `lenai` | Ollama (`OLLAMA_BASE_URL` LAN IP preferred) |

**Gmail:** all of Client ID/Secret/Refresh Token; **no** sync label for All Mail.
