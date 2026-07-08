# Changelog

All notable changes to **monsoon** are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed

- WAHA `list_chats`: use `sortBy=conversationTimestamp` (was invalid `messageTimestamp` → 400).
- Auto-enable NOWEB `store` on WAHA session config for chat/message history APIs.
- Empty `GMAIL_SYNC_MAX_PAGES` env no longer crashes app startup (treat as unset).
- Container DNS on `app` service for WAHA WhatsApp connectivity (`EAI_AGAIN web.whatsapp.com`).
- Parser keyword aliases: `to do`/`to-do`, `remind me to`, `complete`/`finish`, `show`/`tasks`, `summary`, `?`.
- Commit outbound message immediately after send so echo webhooks see sent state.
- CI/docker-publish: smoke-import app and built image to catch driver mismatches before deploy.
- `/health/webhook` — shows current vs expected webhook URL and session status.
- Self-chat reply: fall back to `me.id` when `remoteJidAlt` missing on `@lid` messages.
- WAHA `sendText` failures now log HTTP status + response body.
- Portainer: `pull_policy: always` on app image so redeploy pulls latest GHCR build.
- Docker DNS: fixed `container_name` (`monsoon-app`, `monsoon-waha`) and network `monsoon`.
- Self-chat capture: resolve `@lid` sender via `me.id` so allowed-number check passes.
- Webhook subscribes to `message.any` (required for Message-yourself on WAHA NOWEB).
- Webhook script sends `X-Api-Key` header to monsoon.
- Deploy docs: SSH tunnel, WAHA Core session naming, webhook troubleshooting.

### Added

- Gmail ingestion: `email_threads`, `email_messages`, `email_participants`, `gmail_sync.py`, OAuth setup script.
- `infra/scripts/wa_backfill.py` — paginated WAHA backfill with resume cursors per chat.
- `/health/wa-index` — index counts; regex entity extract (phone, email, url).
- `docs/whatsapp-backfill.md` — operator guide.
- `docker-compose.portainer.yml` for Portainer stack deploy on notcoolio.
- `docs/deploy-portainer.md` — full Portainer + dedicated WAHA (port 13000) guide.
- `MONSOON_ALLOW_SELF_CHAT` — capture via WhatsApp “Message yourself”.
- Models: users, tasks, inbound/outbound messages, task events.
- `infra/scripts/configure_waha_webhook.py` for session webhook setup.
- Parser unit tests.
- Parallel work playbook: `docs/parallel-work.md`, handoff briefs `docs/handoff/oc-*.md`, lock board `docs/handoff/STATUS.md` (Cursor + OpenCode, LLM Phase A).

## [0.0.0] — 2026-07-07

### Added

- Initial GitHub repository with MIT license.
