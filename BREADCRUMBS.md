# BREADCRUMBS — monsoon

**Updated:** 2026-07-08 07:20

## Next action (operator)

1. **Portainer:** Pull/redeploy `monsoon-app` (`ghcr.io/githubphadnis/monsoon:main` @ `54c623d`)
2. **Retry WA backfill:**
   ```bash
   docker exec monsoon-app python infra/scripts/wa_backfill.py --max-chats 5
   curl -s http://127.0.0.1:8080/health/wa-index | python3 -m json.tool
   ```
3. **Smoke:** `digest`, `reflect griham`, `todo smoke test`

## Shipped on main

- LLM Phase A (context slice, digest, reflect)
- WorkFlowy push mirror
- WA backfill `status@broadcast` contact dedupe fix

## Branch

- `main` @ `54c623d` — pushed to origin; GHCR build should run
