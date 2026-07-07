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

Set `WAHA_SESSION=monsoon` (not `default`).

7. **Deploy the stack**.

Stack name suggestion: `monsoon`.

---

## 3. Pair WhatsApp (dedicated monsoon WAHA)

1. On notcoolio: `http://127.0.0.1:13000/dashboard` (SSH tunnel or LAN).
2. Log in with `WAHA_DASHBOARD_USERNAME` / `WAHA_DASHBOARD_PASSWORD`.
3. Create session **`monsoon`** (matches `WAHA_SESSION` default).
4. Scan QR / pair — this is **only** for monsoon, not other projects.

---

## 4. Wire WAHA webhook → monsoon app

From a host that can reach the stack (notcoolio shell):

```bash
export WAHA_BASE_URL=http://127.0.0.1:13000
export WAHA_API_KEY=<your-key>
export WAHA_SESSION=monsoon

python infra/scripts/configure_waha_webhook.py \
  --webhook-url http://app:8080/api/webhooks/waha
```

Run inside the stack network if `127.0.0.1` session API is used from host; the webhook URL
must be reachable **from the WAHA container** — use Docker service hostname `app` on port
`8080` (as above).

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
