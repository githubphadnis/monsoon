# WhatsApp history backfill (Priority 3)

Index **all** WhatsApp chats and messages from WAHA into Postgres for search,
contacts, and later Ollama extraction (5W1H).

## Tables

| Table | Purpose |
|-------|---------|
| `wa_chats` | One row per chat; backfill cursor per chat |
| `wa_messages` | Full message history (deduped by WAHA message id) |
| `wa_contacts` | JIDs, phones, display names derived from chats/messages |
| `extracted_entities` | Phones, emails, URLs regex-extracted from bodies |
| `sync_state` | Reserved for future global cursors |

## Run on notcoolio

After deploy (tables created on app startup via `init_db()`):

```bash
# Index stats
curl -s http://127.0.0.1:8080/health/wa-index | python3 -m json.tool

# Pilot: first 5 chats
docker exec monsoon-app python infra/scripts/wa_backfill.py --max-chats 5

# Full backfill (may take hours — rate-limited)
docker exec monsoon-app python infra/scripts/wa_backfill.py --full

# Resume / delta: continues from stored offset per chat
docker exec monsoon-app python infra/scripts/wa_backfill.py

# Single chat
docker exec monsoon-app python infra/scripts/wa_backfill.py --chat-id 918291882204@c.us
```

## Env (optional)

| Variable | Default | Meaning |
|----------|---------|---------|
| `MONSOON_WA_BACKFILL_CHAT_PAGE_SIZE` | 50 | Chats per WAHA request |
| `MONSOON_WA_BACKFILL_MESSAGE_PAGE_SIZE` | 100 | Messages per page |
| `MONSOON_WA_BACKFILL_REQUEST_DELAY_MS` | 250 | Pause between WAHA calls |
| `MONSOON_WA_BACKFILL_EXTRACT_ENTITIES` | true | Regex phones/emails/URLs |

## WAHA API

- `GET /api/{session}/chats?limit=&offset=&sortBy=conversationTimestamp&sortOrder=desc`
- `GET /api/{session}/chats/{chatId}/messages?limit=&offset=&downloadMedia=false`

Engine: **NOWEB** (your stack). **NOWEB store must be enabled** on the WAHA session
(`config.noweb.store.enabled=true`) — monsoon sets this on startup via webhook reconciler.
History depth depends on what WAHA has synced locally (~3 months with `fullSync=false`).

## Next (3b)

- Ollama batch: 5W1H structured extract per thread
- Link `wa_messages` to `tasks` / WorkFlowy context children
- Nightly cron container or APScheduler job
