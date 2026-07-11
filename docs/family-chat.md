# Family / peer chat — son on your 1:1

monsoon does **not** open a separate WhatsApp account for your son. WAHA is paired to
**your** number. Every message that hits that WhatsApp (including his 1:1 with you)
is delivered to the webhook. monsoon then **filters** by allowlist.

```text
Son's phone ──WhatsApp──► Your WhatsApp (WAHA session)
                                │
                                ▼
                         monsoon webhook
                                │
              ┌─────────────────┴─────────────────┐
              │ chat in ALLOWED_WHATSAPP_CHAT_IDS? │
              │ sender in ALLOWED_WHATSAPP_NUMBERS?│
              └─────────────────┬─────────────────┘
                                │ yes
                                ▼
                     reply in the same 1:1 chat
```

## Why “nothing happened”

Usually one of:

1. **Chat not on allowlist** — need `<son_digits>@c.us` in `ALLOWED_WHATSAPP_CHAT_IDS`
2. **Number not on allowlist** — same digits in `ALLOWED_WHATSAPP_NUMBERS`
3. **Wrong JID** — WhatsApp often uses opaque `@lid`; monsoon maps via `remoteJidAlt`.
   Still put the **real phone** `@c.us` in env (not the lid).
4. **Stack not redeployed** after env change
5. **He messaged a different WhatsApp** than the one WAHA is logged into

## Portainer env (example)

```env
ALLOWED_WHATSAPP_NUMBERS=918291882204,91XXXXXXXXXX
ALLOWED_WHATSAPP_CHAT_IDS=918291882204@c.us,91XXXXXXXXXX@c.us
MONSOON_ALLOW_SELF_CHAT=true
```

- First entry = you (Message yourself)
- Second = son (your existing 1:1)

Redeploy after changing env.

## Find his chat id

On notcoolio:

```bash
curl -s -H "X-Api-Key: $WAHA_API_KEY" \
  "http://127.0.0.1:3000/api/prakalp/chats?limit=30&sortBy=conversationTimestamp&sortOrder=desc" \
  | python3 -m json.tool | less
```

Look for his name / number. Prefer an id ending in `@c.us` (or `@s.whatsapp.net` — monsoon
normalizes). If you only see `@lid`, still use his real phone as `91…@c.us` in env;
inbound payloads usually include `remoteJidAlt` with the phone JID.

Confirm monsoon loaded the allowlist:

```bash
curl -s http://127.0.0.1:8080/health/ready | python3 -m json.tool
# or
docker logs monsoon-app --tail 100 | grep -E 'chat_not_allowed|Rejected sender|Processing capture'
```

Have him send `help` in the 1:1, then watch logs for `Processing capture` vs `chat_not_allowed`
vs `Rejected sender`.

## Behaviour rules

| Who / where | monsoon |
|-------------|---------|
| You → Message yourself | Commands + digests (your tasks) |
| Son → your 1:1 | Commands (his own task user) |
| You → typing in his 1:1 | **Ignored** (`from_me_peer`) — family chat stays human |
| Anyone else | Ignored (not on allowlist) |

## Smoke

From **his** phone, in **your** 1:1:

```text
help
todo buy notebooks
list today
```

You should see a monsoon reply in that same chat. Your Message-yourself thread stays separate.
