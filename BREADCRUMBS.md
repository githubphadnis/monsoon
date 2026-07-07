# BREADCRUMBS — monsoon

**Updated:** 2026-07-07

## Next action (start here)

1. GitHub Actions green → Portainer **Pull and redeploy**.
2. `docker logs monsoon-app --tail 10` — should show Uvicorn running, not psycopg2 traceback.
3. `docker exec monsoon-waha curl -sS http://127.0.0.1:8080/health/live`

## Session summary

- App crash: `postgresql://` URL used psycopg2 driver but image has psycopg v3 only.
- Fixed `db.py` URL normalization + CI smoke import on built Docker image.

## Branch / state

- `main` — pending push/deploy with psycopg fix.
