# monsoon

Personal **Capture & Reminder** system: WhatsApp in, WorkFlowy mirror, reminders out.

**Stack:** FastAPI · Postgres · WAHA · WorkFlowy API · **Ollama (lenai)** · Docker on `notcoolio`

## Prerequisites

- Docker and Docker Compose on `notcoolio` (Portainer optional)
- [WorkFlowy API key](https://workflowy.com/api-key)
- WAHA instance (included in `docker-compose.yml` or external)
- WhatsApp number paired to WAHA session

## Quick start (local / notcoolio)

```bash
git clone https://github.com/githubphadnis/monsoon.git
cd monsoon
cp .env.example .env
# Edit .env — set WORKFLOWY_API_KEY, WAHA_API_KEY, ALLOWED_WHATSAPP_NUMBERS, etc.

docker compose up -d --build
curl -s http://127.0.0.1:8080/health/live
```

## Architecture overview

```
WhatsApp  →  WAHA  →  webhook  →  monsoon app  →  Postgres
                                      ↓     ↑
                                 Ollama (lenai) — parse, digest, nudges
                                      ↓
                                 WorkFlowy API
                                      ↓
WhatsApp  ←  WAHA  ←  sendText   ←  scheduler / replies
```

- **Postgres** is the source of truth.
- **WorkFlowy** is the mirrored outline for humans.
- **WAHA** handles WhatsApp session and HTTP API.

## Project structure

```
monsoon/
├── app/                    # FastAPI application
│   ├── api/                # HTTP routes (webhook, health)
│   ├── integrations/       # WorkFlowy, WAHA clients
│   ├── models/             # SQLAlchemy / DB models
│   ├── services/           # Task, reminder, sync logic
│   └── scheduler/          # Due reminders, digest jobs
├── docs/                   # Supplementary docs
├── infra/                  # Deploy helpers
├── docker-compose.yml
├── Dockerfile
├── .env.example
└── AGENTS.md               # Agent entrypoint (read first)
```

## WhatsApp commands (V1)

| Command | Example |
|---------|---------|
| Capture | `todo buy milk tomorrow 8am` |
| Note | `note plumber said friday` |
| List | `list today` |
| Complete | `done 14` |
| Snooze | `snooze 14 tomorrow 9am` |
| Digest | `digest now` |
| Help | `help` |

## Deployment (notcoolio)

1. Clone repo on `notcoolio` (or pull via Portainer stack).
2. Create `.env` from `.env.example` (secrets via Portainer env or file).
3. `docker compose up -d --build`
4. Open WAHA dashboard (bound to localhost); scan QR / pair session.
5. Configure WAHA webhook to monsoon:

```bash
python infra/scripts/configure_waha_webhook.py \
  --webhook-url http://monsoon-app:8080/api/webhooks/waha
```

6. Send `todo test from monsoon` on WhatsApp → expect confirmation reply.

## Documentation

| Doc | Purpose |
|-----|---------|
| [project-manifest.md](./project-manifest.md) | V1 boundary & success criteria |
| [ROADMAP.md](./ROADMAP.md) | Phased delivery plan |
| [dev-docs.md](./dev-docs.md) | Architecture decisions & incidents |
| [handover.md](./handover.md) | Current ops snapshot |
| [docs/llm-integration.md](./docs/llm-integration.md) | Ollama / LLM pipeline |

## License

MIT — see [LICENSE](./LICENSE).
