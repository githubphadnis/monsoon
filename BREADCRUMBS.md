# BREADCRUMBS — monsoon

**Updated:** 2026-07-07

## Next action (start here)

1. GitHub Actions green → Portainer **Pull and redeploy** (full stack — WAHA `network_mode` changed).
2. Verify: `docker exec monsoon-waha curl -sS http://127.0.0.1:8080/health/live`
3. WhatsApp: `todo test monsoon reply`

## Session summary

- Docker DNS between waha and app broken on notcoolio (`monsoon-app` unresolved).
- Fix: WAHA `network_mode: service:app` — localhost sidecar, no Cloudflare.

## Branch / state

- `main` — sidecar networking pushed; pending redeploy on notcoolio.
