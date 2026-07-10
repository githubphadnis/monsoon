# BREADCRUMBS — monsoon

**Updated:** 2026-07-10

## Done

- Assistant UX polish from live WhatsApp sample:
  - Digests no longer feed `## Entities` (stops phone/email dumps)
  - Free-text → conversational `ask` (Ollama + context slice)
  - Bad digest post-filter; quieter acks; list hides URL-only titles
  - WorkFlowy metadata → node note (no system child bullets)
  - WA slice skips `from_me` + bot-reply noise

## Operator after redeploy

1. Redeploy `main` on Portainer (pull latest GHCR).
2. WhatsApp smoke:
   - `digest` → prose about open tasks, **no** phone/email lists
   - `elaborate on …` / `ok what about now?` → assistant answer (not "I didn't catch that")
   - `todo buy milk` → `Saved · #N buy milk`
   - `list today` → no bare MSN URL rows for new captures
3. Optional: delete historical junk task #86 (MSN URL) in DB/WorkFlowy manually.

## Then

- Ephemeral bot-message delete (WAHA API spike) — deferred
- MS-08 snooze; auto-link; morning digest cron

## Branch

- `main` — push when ready
