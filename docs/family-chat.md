# Family / group chat — monsoon spaces

Canonical model + roster: **[`docs/family-model.md`](./family-model.md)**.

## Quick map

| Person | Phone | Personal chat today |
|--------|-------|---------------------|
| Prakalp | `918291882204` | Message yourself (WAHA paired) |
| Rashmi | `918291882206` | 1:1 with monsoon number |
| Prathamesh | `467…` / `918291884406` | 1:1 with monsoon number |
| Family | `120363143633935585@g.us` | Shared (`MONSOON_SHARED_CHAT_IDS`) |

```env
ALLOWED_WHATSAPP_NUMBERS=918291882204,918291882206,918291884406,46704098198
ALLOWED_WHATSAPP_CHAT_IDS=918291882204@c.us,918291882206@c.us,918291884406@c.us,46704098198@c.us,120363143633935585@g.us
MONSOON_SHARED_CHAT_IDS=120363143633935585@g.us
MONSOON_USER_ALIASES=prakalp:918291882204,rashmi:918291882206,prathamesh:46704098198,prathu:46704098198
```

## Auto-delete (chat declutter)

```env
MONSOON_EPHEMERAL_SECONDS=300
MONSOON_EPHEMERAL_DELETE_COMMANDS=true
```

## Smoke

- Rashmi 1:1: `help` → reply → clears ~5 min later.
- Family: `todo @prakalp buy milk` → on Prakalp’s list.
- Personal: `digest` → only that person’s tasks.
