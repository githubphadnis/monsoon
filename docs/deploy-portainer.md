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

## 4. WAHA webhook → monsoon app (automatic)

On startup the **app container** configures WAHA automatically:

- Webhook URL: `http://monsoon-app:8080/api/webhooks/waha` (Docker DNS via `container_name`)
- Events: `message`, `message.any`
- Header: `X-Api-Key` = your `WAHA_API_KEY`

**You do not need manual `curl` webhook setup** after Portainer pull & redeploy.

Requirements:

1. `WAHA_SESSION` in Portainer must match your paired session name (e.g. `prakalp`).
2. WAHA session must be **WORKING** (paired). If app starts before pairing, redeploy the
   `app` container once after QR scan.
3. Stack uses fixed container names (`monsoon-app`, `monsoon-waha`) on network `monsoon`.

Verify after redeploy:

```bash
docker exec monsoon-waha curl -sS http://monsoon-app:8080/health/live
curl -sS -H "X-Api-Key: YOUR_KEY" http://127.0.0.1:13000/api/sessions/prakalp | grep monsoon-app
docker logs monsoon-app --tail 20 | grep -i webhook
```

### Manual override (optional)

Set `MONSOON_AUTO_WEBHOOK=false` and use `infra/scripts/configure_waha_webhook.py` with
`--webhook-url http://monsoon-app:8080/api/webhooks/waha`.

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
