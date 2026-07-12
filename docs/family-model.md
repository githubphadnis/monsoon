# Family model — monsoon spaces & roster

Target roster (operator-confirmed 2026-07-12):

| Person | Phone(s) | Personal space | Commands |
|--------|----------|----------------|----------|
| **Prakalp** | `918291882204` | Message yourself on that number | digest, todo, list, summary, delete, complete, … |
| **Prathamesh** | `46704098198` and/or `918291884406` | Personal channel for *his* list | same |
| **Rashmi** | `918291882206` | Personal channel for *her* list | same |
| **Family** | group `120363143633935585@g.us` (3 Phadnis) | Shared — everyone’s open tasks | same + `@name` assign |

## Multi-WAHA sessions (true Message yourself per person)

Preferred: **one** WAHA container, multiple sessions (free since WAHA 2026.6.1).

1. Dashboard → create sessions `prakalp`, `rashmi`, `prathamesh` → QR each phone.
2. Portainer:

```env
WAHA_SESSION=prakalp
MONSOON_WAHA_SESSION_MAP=918291882204:prakalp,918291882206:rashmi,46704098198:prathamesh,918291884406:prathamesh
ALLOWED_WHATSAPP_NUMBERS=918291882204,918291882206,918291884406,46704098198
ALLOWED_WHATSAPP_CHAT_IDS=918291882204@c.us,918291882206@c.us,918291884406@c.us,46704098198@c.us,120363143633935585@g.us
MONSOON_SHARED_CHAT_IDS=120363143633935585@g.us
```

3. Each person uses **Message yourself** on their own phone. Replies go out on the same session.
4. Family group stays on the primary session (`WAHA_SESSION` / Prakalp’s number must be in the group).

Optional multi-container (old Core that only allows `default`):

```env
MONSOON_WAHA_ENDPOINTS=prakalp:http://127.0.0.1:3000,rashmi:http://127.0.0.1:3001,prathamesh:http://127.0.0.1:3002
```

Monsoon auto-wires webhooks for every session in the map.

## Assignment

```
todo @rashmi book dentist
@prakalp buy PC for P3
todo call Hatim @prakalp
```

Creates the task on the **assignee’s** list (their display `#N`). Ack: `Saved · #3 book dentist → @rashmi`.

## Delete vs ephemeral

| Command | Effect |
|---------|--------|
| `delete 3` / `remove 3` | Soft-deletes **your** task `#3` (status=`deleted`) |
| Ephemeral TTL | Auto-removes WhatsApp **messages** after ~5 min (not tasks) |

## Portainer checklist

1. Numbers + chat JIDs + shared group as above.
2. `MONSOON_USER_ALIASES` for `@` names.
3. Redeploy; smoke each personal chat + family `@assign`.
