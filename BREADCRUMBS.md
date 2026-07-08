# BREADCRUMBS — monsoon

**Updated:** 2026-07-08 10:35

## Done

- Digest/reflect prompts tightened (ban thank-you / category fluff)
- Reminders: `remind_at` → WhatsApp; clear after send (MS-04)
- Background sync sped up for same-day catch-up (Gmail 5m×5 pages, WA 5m×5 chats)
- Gmail: resume incomplete list even after mid-pilot historyId; All Mail when label empty
- Docs: gmail-ingestion, whatsapp-backfill, portainer-env, ROADMAP

## Operator after redeploy

1. **Portainer:** ensure `GMAIL_SYNC_LABEL` is **unset/empty** (not INBOX) so Archive is indexed.
2. Redeploy `main`.
3. Watch:
   - `curl -s http://127.0.0.1:8080/health/scheduler | python3 -m json.tool`
   - `curl -s http://127.0.0.1:8080/health/gmail-index | python3 -m json.tool`
   - `curl -s http://127.0.0.1:8080/health/wa-index | python3 -m json.tool`
4. WhatsApp: `digest` — should be concrete, not "Thank you for sharing…"
5. Smoke reminder: `remind me to test monsoon ping` with a near due (or temporarily set `remind_at` in DB)

## Optional Spam/Trash

`GMAIL_INCLUDE_SPAM_TRASH=true` in Portainer if you want those folders too.

## Then

- Switch back to Griham once indexes are running and digest looks sane
- Later: MS-08 snooze; auto-link; morning digest cron

## Branch

- `main` — push this session
