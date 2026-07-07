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

Set `WAHA_SESSION=default` — **WAHA Core** (free image) only allows the session name
`default`. Use a **dedicated monsoon WAHA container** (port 13000) to avoid clashing with
other stacks; the session name is still `default`.

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
4. Start session **`default`** only (WAHA Core does not allow custom session names like `monsoon`).
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
| `Could not resolve host: app` from waha container | Webhook URL must use `monsoon-app` or app container **IP** (see §4) |
| Wrong port | Use **13000**, not 3000 |
| 404 on `/` | Normal — use **`/dashboard`** |
| Login fails | Check `WAHA_DASHBOARD_PASSWORD` in Portainer env |
| Container restarting | Check logs; confirm `WAHA_DASHBOARD_PASSWORD` and `WHATSAPP_SWAGGER_PASSWORD` are set |
| 422 — only `default` session | **WAHA Core** (free) — use session name **`default`**, not `monsoon` / `prakalp`; set `WAHA_SESSION=default` in Portainer |

---

## 4. Wire WAHA webhook → monsoon app

Your session **name** in the dashboard (e.g. `prakalp`) must match **`WAHA_SESSION`** in
Portainer on the `app` service.

### Option A — curl on notcoolio (easiest)

**Verify WAHA can reach the app** (must return `{"status":"ok"}`):

```bash
docker exec monsoon-waha curl -sS -m 5 http://monsoon-app:8080/health/live
```

If you see `Could not resolve host: app` — the webhook URL must **not** use `http://app:8080`.
Use the app container IP instead:

```bash
APP_IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' monsoon-app)
echo "App IP: $APP_IP"

curl -sS -X PUT "http://127.0.0.1:13000/api/sessions/prakalp" \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: YOUR_WAHA_API_KEY" \
  -d "{
    \"config\": {
      \"webhooks\": [{
        \"url\": \"http://${APP_IP}:8080/api/webhooks/waha\",
        \"events\": [\"message\", \"message.any\"],
        \"customHeaders\": [
          {\"name\": \"X-Api-Key\", \"value\": \"YOUR_WAHA_API_KEY\"}
        ]
      }]
    }
  }"
```

If DNS works (`monsoon-app` resolves), use `http://monsoon-app:8080/api/webhooks/waha` instead of the IP.

Legacy one-liner (only if `app` resolves inside `monsoon-waha`):

```bash
curl -sS -X PUT "http://127.0.0.1:13000/api/sessions/prakalp" \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: YOUR_WAHA_API_KEY" \
  -d '{
    "config": {
      "webhooks": [{
        "url": "http://app:8080/api/webhooks/waha",
        "events": ["message", "message.any"],
        "customHeaders": [
          {"name": "X-Api-Key", "value": "YOUR_WAHA_API_KEY"}
        ]
      }]
    }
  }'
```

`http://app:8080` is the Docker hostname — reachable from the WAHA container, not from your PC.

### Option B — Python script (from a machine with the repo)

```bash
export WAHA_BASE_URL=http://127.0.0.1:13000
export WAHA_API_KEY=<your-key>
export WAHA_SESSION=prakalp

python infra/scripts/configure_waha_webhook.py \
  --webhook-url http://app:8080/api/webhooks/waha
```

### Option C — WAHA dashboard

Session row → **gear** → **Webhooks** → add:

- URL: `http://app:8080/api/webhooks/waha`
- Events: `message`
- Custom header: `X-Api-Key` = same as `WAHA_API_KEY`

### Portainer env (app container)

```text
WAHA_SESSION=prakalp
ALLOWED_WHATSAPP_NUMBERS=918291882204
MONSOON_ALLOW_SELF_CHAT=true
```

Recreate the `app` container after changing env vars.

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
curl -s http://127.0.0.1:8080/health/ready
```

---

## Local dev (not Portainer)

Use `docker-compose.yml` in the repo root — builds `app` from source for development.
