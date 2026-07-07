# Context atlas — monsoon direction

monsoon is not **only** task intelligence. It is Prakalp's **personal context atlas**:
capture from channels you already use, index what happened, extract who/what/when/why,
and use Ollama to help you do better over time.

Tasks are one **lens** on the atlas. Email and full WhatsApp history are others.

OpenLoomi is a **reference architecture**, not a dependency. monsoon grows the same
ideas (multi-source memory, insights, soul prompt) on a smaller, operator-owned stack:
Postgres + WAHA + Gmail + Ollama on lenai.

---

## Prioritized build order (operator)

| # | Theme | Outcome |
|---|--------|---------|
| **1** | **Postgres cleanup** | Remove loop spam; sane task list for daily use |
| **2** | **Gmail ingestion** | All mail indexed; threads, senders, attachments metadata |
| **3** | **WhatsApp backfill** | Read *all* WA history via WAHA; contacts + message index |
| **4** | **Daily use** | Capture, digest, nudges on real data — not empty DB |

---

## Layer model

```text
Channels          Index (canonical)        Intelligence           Surfaces
────────          ─────────────────        ─────────────          ────────
WhatsApp live ──► inbound_messages    ──►  Ollama enrich    ──►  WhatsApp replies
WhatsApp hist ──► wa_messages         ──►  entity extract   ──►  digest / search
Gmail       ──► email_messages      ──►  thread classify  ──►  WorkFlowy mirror
              contacts              ──►  relation hints
              extracted_facts       ──►  proactive nudges
tasks         tasks + task_events   ──►  reminders
```

**Source of truth:** Postgres. WorkFlowy remains human-readable mirror for tasks.
Full message corpora stay queryable in DB (and later optional vector index).

---

## 1 — Postgres cleanup (now)

Scripts:

- `infra/scripts/cleanup_loop_tasks.py --dry-run` then `--apply`
- `infra/scripts/cleanup_postgres.sql` for manual review in psql

On notcoolio:

```bash
docker exec monsoon-app python infra/scripts/cleanup_loop_tasks.py --dry-run
# when happy:
docker exec monsoon-app python infra/scripts/cleanup_loop_tasks.py --apply
```

---

## 2 — Gmail ingestion (next build)

**Goal:** Incremental sync of Prakalp's mailbox into Postgres.

| Piece | Approach |
|-------|----------|
| Auth | Google OAuth2 (refresh token in env / Portainer secret) |
| API | Gmail API `users.messages.list` + `get` (format=metadata/full) |
| Tables | `email_messages`, `email_threads`, `email_participants` |
| Job | APScheduler or cron container: poll every 5–15 min |
| Dedupe | `gmail_message_id` unique |
| LLM | Phase 2b: classify (action / FYI / waiting), extract tasks |

Env (future): `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN`,
`GMAIL_SYNC_LABEL` (e.g. `INBOX` or custom label).

---

## 3 — WhatsApp full history backfill

**Goal:** Index every chat and message — not only webhook `message` events going forward.

| Piece | Approach |
|-------|----------|
| API | WAHA: list chats → paginate messages per `chatId` |
| Tables | `wa_chats`, `wa_messages`, `wa_contacts`, `extracted_entities` |
| Fields | who (JID, phone, display name), when (timestamp), body, media flag, from_me |
| Contacts | Derive from chat list + vCard if WAHA exposes; map JID → `contacts` |
| Extract | Batch Ollama: phones, dates, action items, people, places → `extracted_entities` |
| Job | One-shot backfill script + nightly delta sync |

**5W1H index** (stored as structured JSON per message or per thread summary):

- **who** — participants, mentioned names
- **where** — places, links
- **what** — topic / intent
- **when** — explicit dates in text + message timestamp
- **why** — inferred context (LLM, optional)
- **how** — action type (request, promise, question, info)

Rate-limit WAHA; checkpoint cursor per chat in `sync_state`.

---

## 4 — Start using it

Minimum daily loop after (1):

1. WhatsApp capture: `todo` / `to do` / free text
2. `list today` / `digest` / `done N`
3. Trust Postgres — WorkFlowy mirror when Phase 2 ships

After (2)+(3): morning digest spans **tasks + unread email themes + WA threads**
you care about.

---

## What we still borrow from OpenLoomi (ideas only)

- Soul prompt presets
- Insight → structured JSON → action
- Relation hints (support / compete / duplicate) — later, over `extracted_entities`
- Context **slice** per LLM call — SQL bundle, not a monolithic graph DB

## What we defer

- Multi-tenant, guest accounts, Next.js UI
- Full OpenLoomi connector matrix
- Autonomous agent tool loops
