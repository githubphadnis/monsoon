# BREADCRUMBS — monsoon

**Updated:** 2026-07-07

## Next action (start here)

1. Pull/redeploy `main` (new tables + `PYTHONPATH` for scripts).
2. Pilot backfill: `docker exec monsoon-app python infra/scripts/wa_backfill.py --max-chats 5`
3. Check: `curl -s http://127.0.0.1:8080/health/wa-index`
4. Full run: `wa_backfill.py --full` (hours; rate-limited)

## Direction

Priority 3 shipped in code — operator runs backfill on notcoolio.

## Branch / state

- `main` — WA index tables + backfill script pending deploy
