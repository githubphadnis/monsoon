# BREADCRUMBS — monsoon

**Updated:** 2026-07-07

## Next action (start here)

1. Wait for GitHub Actions green → Portainer **Pull and redeploy** `monsoon` stack.
2. On notcoolio: `curl -s http://127.0.0.1:8080/health/webhook` — expect `"status":"ok"` and `monsoon-app` in `current_urls`.
3. WhatsApp test: `todo test monsoon reply`.

## Session summary

- Event Monitor ≠ webhook delivery. User fixed `WAHA_SESSION=prakalp`; still no reply — likely webhook still pointed at old `app` hostname or image not pulled.
- Shipped: webhook reconciler (60s), `/health/webhook`, sendText error logging, `pull_policy: always`.

## Branch / state

- `main` — pending push with webhook reconciler + diagnostics.
