# Family model — monsoon spaces & roster

Target roster (operator-confirmed 2026-07-12):

| Person | Phone(s) | Personal space | Commands |
|--------|----------|----------------|----------|
| **Prakalp** | `918291882204` | Message yourself on that number | digest, todo, list, summary, delete, complete, … |
| **Prathamesh** | `46704098198` and/or `918291884406` | Personal channel for *his* list | same |
| **Rashmi** | `918291882206` | Personal channel for *her* list | same |
| **Family** | group `120363143633935585@g.us` (3 Phadnis) | Shared — everyone’s open tasks | same + `@name` assign |

## What WhatsApp allows (important)

Monsoon uses **one WAHA session** = **one** paired WhatsApp account.

| Desired | Possible today? |
|---------|-----------------|
| Prakalp Message yourself on `…2204` | Yes — if WAHA is paired to that number |
| Rashmi / Prathamesh Message yourself on *their* phones | **No** on a single WAHA — those chats never hit the server |
| Same people, private lists, full command set | **Yes** — each opens a **1:1 with the monsoon (WAHA) number**, or a private group (person + monsoon only) |
| Family group shared list | Yes — `MONSOON_SHARED_CHAT_IDS` |
| `@prakalp …` assign onto that person’s list | Yes — `MONSOON_USER_ALIASES` + `todo @name …` |

**True “everyone Message yourself on their own number”** needs **multi-WAHA** (one session per phone) — not built yet (tracked as MS-09).

## Recommended setup (single WAHA)

Assume WAHA is paired to Prakalp’s `918291882204`.

```env
ALLOWED_WHATSAPP_NUMBERS=918291882204,918291882206,918291884406,46704098198
ALLOWED_WHATSAPP_CHAT_IDS=918291882204@c.us,918291882206@c.us,918291884406@c.us,46704098198@c.us,120363143633935585@g.us
MONSOON_SHARED_CHAT_IDS=120363143633935585@g.us
MONSOON_USER_ALIASES=prakalp:918291882204,rashmi:918291882206,prathamesh:46704098198,prathu:46704098198,prathamesh_in:918291884406
```

| Who | Where they type |
|-----|-----------------|
| Prakalp | Message yourself (`…2204@c.us`) |
| Rashmi | 1:1 chat with `…2204` (her messages attributed to `…2206`) |
| Prathamesh | 1:1 with `…2204` from Sweden or India number |
| Everyone | 3 Phadnis group for shared / assign |

Optional private groups (`Monsoon — Rashmi` = Rashmi + monsoon only) instead of 1:1 clutter — allowlist those `@g.us` JIDs.

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
