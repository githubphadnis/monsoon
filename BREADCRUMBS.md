# BREADCRUMBS — monsoon

**Updated:** 2026-07-07

## Next action (start here)

1. Wait for GitHub Actions → GHCR publish green, then Portainer **Pull and redeploy** `app`.
2. Re-run webhook curl with `message` + `message.any` (see `docs/deploy-portainer.md` §4).
3. WhatsApp test: `todo test monsoon reply`.

## Session summary

- Portainer deploy **OK**; Postgres **OK**; WAHA dashboard blocked by **localhost-only bind** (`127.0.0.1:13000`).

## Branch / state

- Remote: `main` on GitHub; GHCR image published.
- notcoolio: stack deployed (user confirmed).
