# monsoon

Personal **Capture & Reminder** system: WhatsApp in, WorkFlowy mirror, reminders out.

**Stack:** FastAPI · Postgres · WAHA · WorkFlowy API · **Ollama (lenai)** · Docker on `notcoolio`

## Prerequisites

- Docker and Portainer on **notcoolio**
- GitHub Actions publishes `ghcr.io/githubphadnis/monsoon:main`
- **Dedicated monsoon WAHA** (this stack only — port **13000**)
- [WorkFlowy API key](https://workflowy.com/api-key) (Phase 2+)
- Ollama on **lenai** (`OLLAMA_BASE_URL`)
## Deploy on notcoolio (Portainer)

**Production path:** GitHub Actions builds the app image → GHCR → Portainer stack pull.
**Do not** `docker compose build` on the server for production.

Full guide: **[docs/deploy-portainer.md](./docs/deploy-portainer.md)**

### Summary

1. Push to `main` → Actions publish `ghcr.io/githubphadnis/monsoon:main`
2. Portainer → Add stack from Git → `docker-compose.portainer.yml`
3. Set stack env vars (`POSTGRES_PASSWORD`, `WAHA_*`, `ALLOWED_WHATSAPP_NUMBERS`, …)
4. Pair **dedicated monsoon WAHA** at `http://notcoolio:13000/dashboard` (session `monsoon`)
5. Configure webhook → `http://app:8080/api/webhooks/waha`
6. In **WhatsApp**, message yourself (or the paired number): `todo call bank tomorrow 10am`

### Where messages go

| You type here | monsoon replies here |
|---------------|----------------------|
| **WhatsApp** on your phone (Message yourself, or chat with paired number) | **Same WhatsApp chat** |

There is no monsoon web UI for capture in v1.

### Local dev only

```bash
cp .env.example .env
docker compose up -d --build   # builds from source; not used on Portainer
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

## Documentation

| Doc | Purpose |
|-----|---------|
| [project-manifest.md](./project-manifest.md) | V1 boundary & success criteria |
| [ROADMAP.md](./ROADMAP.md) | Phased delivery plan |
| [dev-docs.md](./dev-docs.md) | Architecture decisions & incidents |
| [docs/deploy-portainer.md](./docs/deploy-portainer.md) | Portainer + GHCR deploy on notcoolio |
| [docs/llm-integration.md](./docs/llm-integration.md) | Ollama / LLM pipeline |

## License

MIT — see [LICENSE](./LICENSE).
