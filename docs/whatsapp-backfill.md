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
| `MONSOON_WA_SYNC_INTERVAL_MINUTES` | 5 | Background batch interval |
| `MONSOON_WA_SYNC_BATCH_CHATS` | 5 | Chats per background tick |

Background scheduler advances a chat-list cursor (`sync_state` key
`wa_backfill:chat_list_offset`) so small batches progress across the full session.

## Fast catch-up (individual corpora)

Background defaults (5 chats / 5 min) are deliberately gentle. For a same-day fill:

**1. One-shot per WAHA session** (fastest; run in Portainer console / SSH):

```bash
# Primary (Prakalp)
docker exec monsoon-app python infra/scripts/wa_backfill.py --full

# Secondary sessions (case-sensitive names from WAHA dashboard)
docker exec monsoon-app python infra/scripts/wa_backfill.py --full --session Rashmi
docker exec monsoon-app python infra/scripts/wa_backfill.py --full --session Prathamesh

# Priority 1:1 / Message yourself first
docker exec monsoon-app python infra/scripts/wa_backfill.py --chat-id 918291882204@c.us --session prakalp
```

Progress prints to stderr while the run is live (chat name, message offset, +msgs,
elapsed). JSON summary prints on stdout when finished. Use `--quiet` to hide progress.

**2. Or crank background sync in Portainer** (then redeploy):

```env
MONSOON_WA_SYNC_INTERVAL_MINUTES=1
MONSOON_WA_SYNC_BATCH_CHATS=25
MONSOON_WA_BACKFILL_MESSAGE_PAGE_SIZE=200
MONSOON_WA_BACKFILL_REQUEST_DELAY_MS=50
```

After catch-up, dial back toward `INTERVAL=5` / `BATCH=5–10` so WAHA stays quiet overnight.

Watch: `curl -s http://127.0.0.1:8080/health/wa-index | python3 -m json.tool`

### Size & risk notes

| Concern | Reality |
|---------|---------|
| Postgres size | Fine for household scale. Roughly **0.5–3 KB/msg** with `raw` JSONB; ~100k msgs ≈ hundreds of MB, not tens of GB. |
| Biggest growth | Per-message `raw` JSONB (full WAHA payload). Bodies alone are cheap. |
| Hard ceiling | NOWEB store depth (`fullSync=false` ≈ months on device). Monsoon cannot invent older history WAHA never synced. |
| Going too hard | WAHA/API timeouts, disc spike, or WhatsApp rate pressure on the linked phones — bump delay if you see 5xx / disconnects. |

Multi-session: each phone’s session builds **its own** `session=` corpus. Family groups appear on every member who is in that group.

### LLM query caveat

Personal `ask` / `reflect` today lean on **tasks**, not the full WA index (privacy isolation). Filling the corpus is necessary but not sufficient for “ask me what X said” — that needs person-scoped WA in the ask path (next unlock).

Also: `curl -s http://127.0.0.1:8080/health/scheduler | python3 -m json.tool`

## WAHA API

- `GET /api/{session}/chats?limit=&offset=&sortBy=conversationTimestamp&sortOrder=desc`
- `GET /api/{session}/chats/{chatId}/messages?limit=&offset=&downloadMedia=false`

Engine: **NOWEB** (your stack). **NOWEB store must be enabled** on the WAHA session
(`config.noweb.store.enabled=true`) — monsoon sets this on startup via webhook reconciler.
History depth depends on what WAHA has synced locally (~3 months with `fullSync=false`).

## Next (3b)

- Ollama batch: 5W1H structured extract per thread
- Link `wa_messages` to `tasks` / WorkFlowy context children
