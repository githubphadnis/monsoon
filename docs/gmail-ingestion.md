# Gmail ingestion (Priority 2)

Sync your mailbox into Postgres for the context atlas (threads, messages,
participants, regex entity extract).

## 1. Google Cloud setup (one-time)

1. [Google Cloud Console](https://console.cloud.google.com/) → create/select project
2. **APIs & Services** → enable **Gmail API**
3. **OAuth consent screen** — External or Internal; add scope `gmail.readonly`
4. **Credentials** → **Create credentials** → **OAuth client ID** → **Desktop app**
5. Download JSON or copy Client ID + Client Secret

## 2. Refresh token (run on your PC)

```bash
cd monsoon
pip install google-auth-oauthlib google-api-python-client
python infra/scripts/gmail_oauth_setup.py --client-secrets path/to/client_secret.json
```

Copy `GMAIL_REFRESH_TOKEN` into Portainer (treat as secret).

## 3. Portainer env

```text
GMAIL_CLIENT_ID=...
GMAIL_CLIENT_SECRET=...
GMAIL_REFRESH_TOKEN=...
GMAIL_SYNC_LABEL=INBOX          # optional — omit or empty for all mail
GMAIL_SYNC_PAGE_SIZE=50
GMAIL_SYNC_MAX_PAGES=           # optional pilot cap
```

Redeploy stack after adding vars.

## 4. Sync on notcoolio

```bash
# Config + counts
curl -s http://127.0.0.1:8080/health/gmail-index | python3 -m json.tool

# Pilot (2 pages)
docker exec monsoon-app python infra/scripts/gmail_sync.py --max-pages 2

# Full initial sync (resume via sync_state page token if interrupted)
docker exec monsoon-app python infra/scripts/gmail_sync.py --full

# Incremental (uses Gmail historyId after first successful sync)
docker exec monsoon-app python infra/scripts/gmail_sync.py
```

## Tables

| Table | Content |
|-------|---------|
| `email_threads` | Gmail thread id, subject, snippet |
| `email_messages` | From, to, cc, subject, snippet, headers |
| `email_participants` | Unique email addresses |
| `sync_state` | `gmail:history_id`, `gmail:list_page_token` |

## Next (2b)

- LLM classify: action / FYI / waiting
- Promote email → task / WorkFlowy context child
- Scheduled sync (cron / APScheduler every 15 min)
