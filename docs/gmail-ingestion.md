# Gmail ingestion

Sync mailbox into Postgres for the context atlas (threads, messages, participants,
entity extract). Background scheduler continues indexing in small batches until done.

## Mailbox coverage

| Mode | Env | What gets indexed |
|------|-----|-------------------|
| **All mail (recommended)** | Leave `GMAIL_SYNC_LABEL` **empty / unset** | Inbox + **Archive** + sent + etc. Everything except Spam/Trash |
| Inbox only | `GMAIL_SYNC_LABEL=INBOX` | Inbox only — archived mail skipped |
| Include Spam/Trash | `GMAIL_INCLUDE_SPAM_TRASH=true` | Also Spam and Trash |

**Operator note:** for a complete personal atlas, use empty label (All Mail). Do **not** set
`INBOX` if you want archived threads.

## 1. Google Cloud setup (one-time)

1. [Google Cloud Console](https://console.cloud.google.com/) → create/select project
2. Enable **Gmail API**
3. **OAuth consent screen** — Testing is fine for personal use; add yourself as a test user
4. **Credentials** → **OAuth client ID** → **Desktop app**
5. Download JSON

Exact click-path: see session notes — Desktop app + Advanced approval on the warning screen.

## 2. Refresh token (run on your PC)

```bash
cd monsoon
python infra/scripts/gmail_oauth_setup.py --client-secrets "C:\Users\you\Downloads\client_secret.json"
```

Copy printed `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN` into Portainer.

## 3. Portainer env

```text
GMAIL_CLIENT_ID=...
GMAIL_CLIENT_SECRET=...
GMAIL_REFRESH_TOKEN=...
# Leave UNSET for All Mail (archive included):
# GMAIL_SYNC_LABEL=
GMAIL_SYNC_PAGE_SIZE=50
# Optional same-day catch-up (defaults already aggressive):
MONSOON_GMAIL_SYNC_INTERVAL_MINUTES=5
MONSOON_GMAIL_SYNC_BATCH_PAGES=5
# Optional:
# GMAIL_INCLUDE_SPAM_TRASH=true
```

Redeploy stack after adding vars.

## 4. Sync

Manual:

```bash
curl -s http://127.0.0.1:8080/health/gmail-index | python3 -m json.tool
docker exec monsoon-app python infra/scripts/gmail_sync.py --max-pages 5
```

Background (default after MS-03): loops every N minutes, batch of pages;
resumes incomplete list even if a historyId was saved mid-pilot.

When `list_sync_in_progress` in health is `false` / absent and message counts stabilize,
initial backlog is done — further runs use Gmail history (delta).

```bash
curl -s http://127.0.0.1:8080/health/scheduler | python3 -m json.tool
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
