# Deploy monsoon on notcoolio (Portainer)

monsoon is deployed as a **Portainer stack** from GitHub. The **app image** is built by
**GitHub Actions** and published to **GHCR**. Portainer pulls that image — it does not
build on the server.

**WAHA:** this stack includes a **dedicated monsoon WAHA** (`monsoon_waha_sessions` volume,
host port **13000**). Do not point it at Moneypenny or any other WAHA instance.

---

## 1. GitHub Actions (automatic)

On every push to `main`:

1. `ci.yml` — lint + tests (PRs and pushes)
2. `docker-publish.yml` — tests, then build + push:
   - `ghcr.io/githubphadnis/monsoon:main`
   - `ghcr.io/githubphadnis/monsoon:latest`
   - `ghcr.io/githubphadnis/monsoon:main-<sha>`

After the first successful publish, make the GHCR package **public** (or add registry
credentials in Portainer):

GitHub → Packages → `monsoon` → Package settings → Change visibility → Public.

---

## 2. Portainer — create stack

1. Open Portainer on **notcoolio**.
2. **Stacks** → **Add stack** → **Git repository**.
3. Repository URL: `https://github.com/githubphadnis/monsoon`
4. Repository reference: `refs/heads/main`
5. Compose path: `docker-compose.portainer.yml`
6. **Environment variables** (stack env) — use [`docs/portainer-env.example`](./portainer-env.example) as the checklist. **Required:**

| Variable | Required |
|----------|----------|
| `POSTGRES_PASSWORD` | yes |
| `WAHA_API_KEY` | yes |
| `WAHA_DASHBOARD_PASSWORD` | yes |
| `WHATSAPP_SWAGGER_PASSWORD` | yes |
| `ALLOWED_WHATSAPP_NUMBERS` | yes |

`DATABASE_URL`, `APP_HOST`, `APP_PORT`, `WAHA_WEBHOOK_PATH`, cron vars are **not** used by `docker-compose.portainer.yml` (safe to omit).

Set `WAHA_SESSION=prakalp` (or whatever name you pair in the dashboard). Compose default is `prakalp`.
If WAHA Core rejects custom session names, use `default` and set `WAHA_SESSION=default` to match.

7. **Deploy the stack**.

Stack name suggestion: `monsoon`.

---

## 3. Pair WhatsApp (dedicated monsoon WAHA)

WAHA is published as **`127.0.0.1:13000`** on notcoolio (not on all interfaces). From your
laptop you **cannot** open `http://notcoolio:13000` — use an SSH tunnel:

```bash
# On your PC (keep this terminal open)
ssh -L 13000:127.0.0.1:13000 prakalp@notcoolio
```

Then in your browser:

1. Open **`http://127.0.0.1:13000/dashboard`** (port **13000**, path **`/dashboard`**).
2. Log in with `WAHA_DASHBOARD_USERNAME` / `WAHA_DASHBOARD_PASSWORD` (default user: `admin`).
3. When prompted, enter **`WAHA_API_KEY`** (same value as in Portainer stack env).
4. Start session **`prakalp`** (must match `WAHA_SESSION` in Portainer).
5. Scan QR / pair — this WAHA instance is **only** for monsoon, not other projects.

### Dashboard won't load?

On notcoolio shell:

```bash
docker ps --filter name=waha --format '{{.Names}} {{.Status}} {{.Ports}}'
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:13000/dashboard
docker logs "$(docker ps -q --filter name=waha | head -1)" --tail 80
```

| Symptom | Likely cause |
|---------|----------------|
| Browser timeout / connection refused from PC | No SSH tunnel; WAHA is localhost-only on notcoolio |
| `Could not resolve host` from waha → app | Old stack layout — pull latest compose; WAHA now shares app's network via `127.0.0.1` |
| Wrong port | Use **13000**, not 3000 |
| 404 on `/` | Normal — use **`/dashboard`** |
| Login fails | Check `WAHA_DASHBOARD_PASSWORD` in Portainer env |
| Container restarting | Check logs; confirm `WAHA_DASHBOARD_PASSWORD` and `WHATSAPP_SWAGGER_PASSWORD` are set |
| `EAI_AGAIN web.whatsapp.com` in WAHA logs | Container DNS — compose sets `127.0.0.11` + `1.1.1.1`; test host DNS |
| `list_chats` 400 on backfill | Redeploy latest `main` — fixed `sortBy` + NOWEB store auto-config |
| App crash `gmail_sync_max_pages` | Omit `GMAIL_SYNC_MAX_PAGES` in Portainer or redeploy latest `main` |
| 422 — only `default` session | **WAHA Core** tier — try `WAHA_SESSION=default` or upgrade tier |

---

## 4. WAHA webhook → monsoon app (automatic)

**Networking:** WAHA uses `network_mode: service:app` — it shares the app container's
network namespace. Webhooks and API calls use **`127.0.0.1`** (no Docker DNS between
WAHA and app). This is a standard sidecar pattern when two containers must talk
reliably; Cloudflare tunnels are **not** needed for internal traffic.

On startup the **app container** configures WAHA automatically:

- Webhook URL: `http://127.0.0.1:8080/api/webhooks/waha`
- Events: `message`, `message.any`
- Header: `X-Api-Key` = your `WAHA_API_KEY`
- NOWEB store: `config.noweb.store.enabled=true` (required for chat/message history backfill)
- App → WAHA: `http://127.0.0.1:3000` (WAHA port published via app as host **13000**)

**You do not need manual `curl` webhook setup** after Portainer pull & redeploy.

Requirements:

1. `WAHA_SESSION` in Portainer must match your paired session name (e.g. `prakalp`).
2. WAHA session must be **WORKING** (paired). If app starts before pairing, redeploy once
   after QR scan.
3. **Full stack redeploy** after compose changes (WAHA `network_mode` change requires
   recreating both `monsoon-app` and `monsoon-waha`).

### Event Monitor shows messages but no WhatsApp reply

WAHA **Event Monitor** only proves WAHA received the message on the phone — it does **not**
prove the webhook reached monsoon. Check:

```bash
curl -s http://127.0.0.1:8080/health/webhook | python3 -m json.tool
docker exec monsoon-waha curl -sS http://127.0.0.1:8080/health/live
docker logs monsoon-app --tail 50 | grep -E 'Webhook received|sendText|webhook'
```

| `health/webhook` | Meaning |
|------------------|---------|
| `"status": "ok"` + `noweb_store_enabled: true` | Webhook + NOWEB store ready for backfill |
| `"status": "ok"` + `current_urls` contains `127.0.0.1:8080` | Webhook wired — check app logs for `sendText` errors |
| `"status": "misconfigured"` + old `app` / `monsoon-app` URL | Wait ~60s (reconciler) or recreate `monsoon-app` |
| `session_not_found` | `WAHA_SESSION` mismatch — must match dashboard session (`prakalp`) |

`WAHA_SESSION=default` while dashboard shows `prakalp` breaks **outbound** replies even if
inbound webhooks work.

Verify after redeploy:

```bash
docker exec monsoon-waha curl -sS http://127.0.0.1:8080/health/live
curl -sS -H "X-Api-Key: YOUR_KEY" http://127.0.0.1:13000/api/sessions/prakalp | grep 127.0.0.1
docker logs monsoon-app --tail 20 | grep -i webhook
```

### Manual override (optional)

Set `MONSOON_AUTO_WEBHOOK=false` and use `infra/scripts/configure_waha_webhook.py` with
`--webhook-url http://127.0.0.1:8080/api/webhooks/waha`.

---

## 5. Where you send messages

On your phone, open **WhatsApp**:

- **Message yourself** (if `MONSOON_ALLOW_SELF_CHAT=true`), or
- Message the number paired to **monsoon’s** WAHA session.

Send:

```text
todo call bank tomorrow 10am
```

Reply appears in the **same WhatsApp chat** (not in Portainer, not on a website).

---

## 6. Updates (redeploy)

After `main` pushes a new image:

1. Portainer → **Stacks** → `monsoon` → **Pull and redeploy** (or enable webhook/auto-update).
2. Or: **Recreate** the `app` container only if you use `:main` tag.

Postgres and WAHA volumes persist across redeploys.

---

## 7. Health checks

```bash
curl -s http://127.0.0.1:8080/health/live
curl -s http://127.0.0.1:8080/health/db
curl -s http://127.0.0.1:8080/health/webhook
curl -s http://127.0.0.1:8080/health/wa-index
curl -s http://127.0.0.1:8080/health/ready   # includes ollama_reachable
```

---

## 8. Ollama on lenai (LLM digest / reflect)

`digest` and `reflect` need **Ollama reachable from inside `monsoon-app`**. Default env:
`OLLAMA_BASE_URL=http://lenai:11434`.

**The problem is Docker DNS, not lenai's location.** The `monsoon-app` container runs on
Docker's bridge network. Hostname `lenai` (mDNS, router DNS, or Tailscale MagicDNS) often
**does not resolve inside the container**, even when `curl http://lenai:11434` works on
the notcoolio **host**.

**Prefer LAN IP when both machines are on the same subnet** (lowest latency, stays local):

```text
OLLAMA_BASE_URL=http://192.168.x.x:11434
```

Find lenai's LAN address on lenai: `hostname -I` or your router's DHCP table.

Use **Tailscale IP** (`100.x.x.x`) only when lenai is **not** reachable via LAN from
notcoolio (remote-only, or different VLANs). Tailscale often uses direct LAN paths when
both nodes are local, but plain LAN IP is simpler when it works.

Alternative: add `extra_hosts` on the `app` service mapping `lenai` → LAN IP (compose change).

On **lenai**, Ollama must listen on all interfaces (not only localhost):

```bash
# /etc/systemd/system/ollama.service.d/override.conf
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
```

### Diagnose on notcoolio

```bash
curl -s http://127.0.0.1:8080/health/ready | python3 -m json.tool
docker exec monsoon-app printenv OLLAMA_BASE_URL OLLAMA_MODEL
docker exec monsoon-app python -c "
import httpx, os
u = os.environ['OLLAMA_BASE_URL'].rstrip('/') + '/api/tags'
try:
    r = httpx.get(u, timeout=5)
    print('OK', r.status_code)
except Exception as e:
    print('FAIL', e)
"
```

| Symptom | Fix |
|---------|-----|
| `digest` shows `*Digest*` + `#N task` list only | SQL fallback — Ollama down |
| `reflect` → "Try again when Ollama is reachable" | Same — fix `OLLAMA_BASE_URL` |
| `FAIL [Errno -2] Name or service not known` | Hostname not visible in container — use **LAN IP** (preferred) or Tailscale IP |
| `Connection refused` | `OLLAMA_HOST=0.0.0.0` on lenai; open firewall if needed |
| `404` on model | Set `OLLAMA_MODEL` to a model pulled on lenai (`ollama list`) |

After fixing Portainer env → **redeploy stack** → retry `digest` / `reflect griham`.

---

## Local dev (not Portainer)

Use `docker-compose.yml` in the repo root — builds `app` from source for development.
