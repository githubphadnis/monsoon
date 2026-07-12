# Family / group chat — monsoon spaces

## Personal channels (one per person)

WAHA is **one** WhatsApp account (the monsoon number). Nobody else can use
“Message yourself” on *their* phone — that never reaches monsoon.

Each person gets a **private channel** with the monsoon number:

| Person | Channel | Space type |
|--------|---------|------------|
| You | Message yourself on the WAHA phone | Personal |
| Wife | 1:1 chat with the monsoon number (or a private group: her + monsoon only) | Personal |
| Son | 1:1 with monsoon (or private group / Todo group) | Personal |
| Family | `3 Phadnis` group | Shared |

### Setup (wife example)

1. She opens WhatsApp → chat with **your monsoon number** → send `help`.
2. Portainer — add her phone and that conversation JID:

```env
ALLOWED_WHATSAPP_NUMBERS=918291882204,918291884406,46704098198
ALLOWED_WHATSAPP_CHAT_IDS=918291882204@c.us,918291884406@c.us,46704098198@c.us,120363410556549299@g.us,120363143633935585@g.us
MONSOON_SHARED_CHAT_IDS=120363143633935585@g.us
```

- `918291882204@c.us` — your Message yourself  
- `918291884406@c.us` — wife’s private 1:1 with monsoon  
- `46704098198@c.us` — son’s private 1:1 (if used)  
- Todo / family groups as before  

Optional: name private groups `Monsoon — Rashmi` / `Monsoon — Prathu` (members: person + monsoon only) and allowlist those `@g.us` JIDs instead of 1:1 — keeps family talk separate from monsoon chatter.

## Two kinds of chat

| Chat type | Env | What each person sees |
|-----------|-----|------------------------|
| **Personal** (Message yourself, private 1:1, private monsoon group, Todo) | in `ALLOWED_WHATSAPP_CHAT_IDS` only | **Own** tasks / digest / ask |
| **Shared family** | also in `MONSOON_SHARED_CHAT_IDS` | **Everyone’s** tasks + this group’s WhatsApp history |

## Auto-delete (keep channels unclogged)

After deploy, monsoon deletes its own replies (and best-effort command messages)
after a TTL via WAHA:

```env
MONSOON_EPHEMERAL_SECONDS=300
MONSOON_EPHEMERAL_DELETE_COMMANDS=true
```

- `0` disables. Default is 5 minutes.
- Bot replies revoke for everyone (clears on their phone too).
- Peer command lines may only clear on the monsoon device; for full wipe on both sides, enable WhatsApp **Disappearing messages** on that personal chat.

## Why son’s digest showed Griham

Previously, digest fed the **global** WhatsApp/email index into Ollama. Fixed:
personal digests use **only that user’s tasks**.

## Shared family group behaviour

In a shared chat:

- `list` / `digest` → all allowlisted members’ open tasks (labeled by phone suffix)
- free-text ask → those tasks + **messages from that group only** (indexed WA)
- each `todo` still saves under the **sender’s** user (attribution)

## Restaurant / “how was lunch?” memory

Indexing of WA history exists (`wa_messages`). Rich multi-opinion group RAG is next.

## Find chat / group ids

Host port **13000**, paste `WAHA_API_KEY` from Portainer — WAHA chats API.

## Smoke

**Wife 1:1:** `help` → reply → ~5 min later reply disappears.  
**Todo group:** son `digest` → only his tasks.  
**Family shared:** `list` → pooled tasks.
