# BREADCRUMBS — monsoon

**Updated:** 2026-07-07 (session end)

## Next action (start here)

1. **Portainer:** Pull and redeploy `main` (latest: `9a5d635` — backfill `sortBy` + NOWEB store).
2. **Verify:** `curl -s http://127.0.0.1:8080/health/webhook` → `"configured": true`, `"noweb_store_enabled": true`.
3. **WA pilot:** `docker exec monsoon-app python infra/scripts/wa_backfill.py --max-chats 5`
4. **Index:** `curl -s http://127.0.0.1:8080/health/wa-index`
5. **Capture smoke:** WhatsApp self-chat `todo redeploy smoke test` (one reply, no loop).

**Defer:** Gmail OAuth + sync until WA pilot succeeds. **Do not** run `--full` backfill yet (huge groups; volume hardening pending).

## Direction

Context atlas — finish **WhatsApp index pilot** on notcoolio, then Gmail operator setup, then WorkFlowy mirror.

## Branch / state

- `main` — deployed stack: sidecar WAHA (`127.0.0.1`), session `prakalp`, Postgres index tables, Gmail code (optional env).
- **Tonight's fixes pushed:** container DNS, empty `GMAIL_SYNC_MAX_PAGES`, `list_chats` sort field, auto NOWEB store on session.
