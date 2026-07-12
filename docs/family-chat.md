# Family / group chat — monsoon spaces

## Two kinds of chat

| Chat type | Env | What each person sees |
|-----------|-----|------------------------|
| **Personal** (Message yourself, Todo chore group, 1:1) | in `ALLOWED_WHATSAPP_CHAT_IDS` only | **Own** tasks / digest / ask |
| **Shared family** | also in `MONSOON_SHARED_CHAT_IDS` | **Everyone’s** tasks + this group’s WhatsApp history |

### Example (your setup)

```env
ALLOWED_WHATSAPP_NUMBERS=918291882204,918291884406,46704098198
ALLOWED_WHATSAPP_CHAT_IDS=918291882204@c.us,120363410556549299@g.us,120363143633935585@g.us
MONSOON_SHARED_CHAT_IDS=120363143633935585@g.us
```

- `918291882204@c.us` — your Message yourself (personal)
- `120363410556549299@g.us` — **Todo** chore group (personal tasks per sender; digests stay private)
- `120363143633935585@g.us` — **3 Phadnis** family group (shared space)

## Why son’s digest showed Griham

Previously, digest fed the **global** WhatsApp/email index into Ollama. The model ignored his
two tasks and summarized *your* atlas. Fixed: personal digests use **only that user’s tasks**.

## Shared family group behaviour

In a shared chat:

- `list` / `digest` → all allowlisted members’ open tasks (labeled by phone suffix)
- free-text ask → those tasks + **messages from that group only** (indexed WA)
- each `todo` still saves under the **sender’s** user (attribution)

## Restaurant / “how was lunch?” memory

Indexing of WA history exists (`wa_messages`). **Group-scoped Q&A with multi-person
opinions** (Sunday lunch → later recommendations) is the next layer: search + summarize
with speaker attribution. Not fully productized yet — shared-chat ask now uses recent
group lines; richer “5 restaurant links + past opinions” needs a dedicated retrieval pass.

## Find group ids

Host port **13000**, paste `WAHA_API_KEY` from Portainer — see earlier runbook / WAHA chats API.

## Smoke

**Todo group (personal):** son `digest` → only his tasks (books, salon), never Griham.

**Family shared group:** after setting `MONSOON_SHARED_CHAT_IDS`, `list` shows everyone’s items.
