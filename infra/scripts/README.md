# infra/scripts

| Script | Purpose |
|--------|---------|
| `cleanup_loop_tasks.py` | Remove self-chat loop spam tasks (`--dry-run` / `--apply`) |
| `cleanup_postgres.sql` | Manual psql preview/delete |
| `configure_waha_webhook.py` | Manual WAHA webhook setup |
| `diagnose_stack.sh` | WAHA → app connectivity on notcoolio |
| `wa_backfill.py` | Index all WA chats/messages — see `docs/whatsapp-backfill.md` |

## Postgres cleanup (Priority 1)

```bash
docker exec monsoon-app python infra/scripts/cleanup_loop_tasks.py --dry-run
docker exec monsoon-app python infra/scripts/cleanup_loop_tasks.py --apply
```

Or via psql:

```bash
docker exec -i monsoon-postgres psql -U monsoon -d monsoon < infra/scripts/cleanup_postgres.sql
```
