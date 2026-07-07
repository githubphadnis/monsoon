# BREADCRUMBS — monsoon

**Updated:** 2026-07-07

## Next action (start here)

1. Wait for GitHub Actions green → Portainer **Pull and redeploy** `monsoon` stack.
2. Confirm `docker logs monsoon-app | grep "WAHA webhook configured"`.
3. WhatsApp test: `todo test monsoon reply`.

## Session summary

- Root cause: WAHA could not resolve hostname `app` — fixed with `container_name` + auto webhook on app startup.

## Branch / state

- `main` — auto webhook + network `monsoon` + containers `monsoon-app` / `monsoon-waha`.
