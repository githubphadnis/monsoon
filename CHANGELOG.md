# Changelog

All notable changes to **monsoon** are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- **MS-09 multi-session WAHA routing:** `MONSOON_WAHA_SESSION_MAP` + optional
  `MONSOON_WAHA_ENDPOINTS`; replies/reminders/ephemeral use the inbound session;
  webhook auto-config for all sessions. See `docs/family-model.md`.
  Startup only requires the **primary** session; missing `rashmi`/`prathamesh`
  sessions no longer block app boot (reconciler retries).
- **Family model docs** (`docs/family-model.md`): roster, personal vs shared, single-WAHA limits.
- **`@alias` assignment** via `MONSOON_USER_ALIASES` (`todo @rashmi …`).
- **`delete` / `remove` / `cancel <id>`** soft-deletes own task.
- **Ephemeral WhatsApp cleanup:** auto-delete monsoon replies (and best-effort
  commands) after `MONSOON_EPHEMERAL_SECONDS` (default 300). See `docs/family-chat.md`.
- **Ollama Auto routing:** optional `OLLAMA_MODEL_PARSE` (fast JSON) + `OLLAMA_MODEL_CHAT`
  (digest/reflect/ask). See `docs/ollama-models.md`. `OLLAMA_CHAT_TIMEOUT_SECONDS` for bigger models.
- Conversational **`ask`** path: free-text / questions use Ollama + context slice instead of "I didn't catch that" or junk todos.
- Digest/reflect post-filter rejects entity-dump / thank-you fluff and falls back to SQL digest.
- Allowlisted groups: prefer @g.us chat id; accept group participants even when only @lid (Todo family chat).
- Webhook: handle only `message.any` (ignore twin `message` events); send WhatsApp ack before WorkFlowy mirror.
- Personal digests/ask use **only that user’s tasks** (no global WA/email leak). `MONSOON_SHARED_CHAT_IDS` pools family tasks + group WA.
- `todo:` / `Todo:` with colon parses as task create.
- Peer 1:1 (family) support: inbound `@lid` resolves via `remoteJidAlt`; `from_me` in non–self chats ignored (`docs/family-chat.md`).
- Reminder scheduler: due `remind_at` → WhatsApp; clears after successful send (idempotent).
- `GMAIL_INCLUDE_SPAM_TRASH`; All Mail when `GMAIL_SYNC_LABEL` empty (Archive included).
- Roadmap build sequence MS-01…08; GitHub milestones V1.0 / V1.1 and issues [#1–#8](https://github.com/githubphadnis/monsoon/issues).
- `docs/roadmap_issues.csv`, `docs/ISSUE_IMPORT.md`, `scripts/create_roadmap_issues.py`.
- Context slice: **Email** section for `digest` / `reflect` (recent messages, topic filter, linked entities).
- Context slice: **Task Context** section sourced from `task_context_items`.
- `/health/gmail-index` reports sync cursor metadata when present.
- `/health/scheduler` reports background Gmail / WA / WorkFlowy / reminder loop state.

### Changed

- Digest/reflect prompts: connected prose (not staccato bullets); ban entity inventories and category fluff.
- Digest context is **tasks-first** with capped email/WA signals; reject support-desk / inbox-topic dumps and replies that ignore open tasks.
- LLM context for digest/reflect/ask **omits `## Entities`**; WA slice skips `from_me` and bot-reply noise.
- Quiet WhatsApp acks (`Saved · #N …` / `Done · #N`); `list` hides URL-only titles.
- WorkFlowy: system metadata goes in the node **note** field (no `id:`/`source:`/`due:`/`status:` children).
- Default soul prompt and background sync intervals tuned for same-day Gmail/WA catch-up.
- Gmail sync resumes incomplete list even if historyId was saved mid-pilot.
- LLM digest/reflect: task titles in replies instead of `Task #N` (context slice title-first).
- WorkFlowy reverse sync now reads task child bullets back into Postgres.
- Background scheduler runs small Gmail, WhatsApp, WorkFlowy, and reminder batches.

### Fixed

- `reflect <topic>` only feeds on-topic tasks (no more merging notebooks into dashcam or padding with infra).
- Ephemeral delete: serialize bare WAHA message hashes to `true_<chatJid>_<hash>` (fixes 500 parseMessageIdSerialized).
- Multi-session: group webhooks only processed by the **primary** WAHA session (stops double capture from Rashmi/Prathamesh fans).
- Gmail `invalid_grant`: raise clean auth pause without ERROR traceback spam; WhatsApp still works.
- Quiet WhatsApp acks no longer show `#N` on Saved/Done/Deleted (numbers remain on `list`).
- Gmail sync: dedupe `email_participants` already pending in the current DB flush.
- WhatsApp background backfill remembers chat-list cursor so small batches progress across chats.
- WA backfill: duplicate `wa_contacts` for `status@broadcast` — contact cache + preload + skip self JID.
- CI: unused import in `workflowy_mirror.py` blocked GHCR publish.
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
- **LLM Phase A:** context slice, Ollama digest/reflect, WhatsApp `reflect <topic>`, LLM digest with SQL fallback.
- **WorkFlowy push mirror:** client, mirror service, `task_context_items`; sync on create, `note <id>`, `done`.
- Parallel work playbook: `docs/parallel-work.md`, handoff briefs `docs/handoff/oc-*.md`, lock board `docs/handoff/STATUS.md` (Cursor + OpenCode, LLM Phase A).

## [0.0.0] — 2026-07-07

### Added

- Initial GitHub repository with MIT license.
