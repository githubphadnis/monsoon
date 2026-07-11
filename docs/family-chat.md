# Family / group chat — monsoon with your son

monsoon does **not** open a separate WhatsApp account. WAHA is paired to **your**
number. Messages in allowed chats hit the webhook; monsoon filters by allowlist.

## Two different allowlists

| Env | Meaning | Example |
|-----|---------|---------|
| `ALLOWED_WHATSAPP_NUMBERS` | **People** who may command monsoon (digits only, no `+`) | `918291882204,918291884406,46704098198` |
| `ALLOWED_WHATSAPP_CHAT_IDS` | **Conversations** where monsoon replies | self-chat `…@c.us` **and/or** group `…@g.us` |

### Group “Todo” (recommended family surface)

```env
ALLOWED_WHATSAPP_NUMBERS=918291882204,918291884406,46704098198
ALLOWED_WHATSAPP_CHAT_IDS=918291882204@c.us,120363410556549299@g.us
MONSOON_ALLOW_SELF_CHAT=true
```

- `918291882204@c.us` = your Message yourself  
- `120363410556549299@g.us` = WhatsApp group named **Todo**  

Do **not** put member phones in `CHAT_IDS` for a group — only the group JID.

### 1:1 instead of a group

```env
ALLOWED_WHATSAPP_CHAT_IDS=918291882204@c.us,46704098198@c.us
```

## Find group id (notcoolio)

WAHA on host port **13000** (not 3000). Paste API key from Portainer:

```bash
curl -sS -H "X-Api-Key: PASTE_KEY" \
  "http://127.0.0.1:13000/api/prakalp/chats?limit=100&sortBy=conversationTimestamp&sortOrder=desc" \
  | python3 -c "
import json,sys
data=json.loads(sys.stdin.read())
chats=data if isinstance(data,list) else data.get('chats') or data.get('data') or []
for c in chats:
    name=c.get('name') or c.get('subject') or ''
    cid=c.get('id') or c.get('jid') or ''
    if 'todo' in str(name).lower() or str(cid).endswith('@g.us'):
        print(repr(name), cid)
"
```

## Verify after Portainer redeploy

```bash
curl -s http://127.0.0.1:8080/health/ready | python3 -m json.tool
```

`allowed_whatsapp_chat_ids` must include `120363410556549299@g.us`.

Have him send `help` in **Todo**, then:

```bash
docker logs monsoon-app --tail 80 | grep -E 'chat_not_allowed|Rejected sender|Processing capture|from_me_peer'
```

| Log | Fix |
|-----|-----|
| `chat_not_allowed` … `chat_id=120363…@g.us` | Add that exact id to `CHAT_IDS`, redeploy |
| `Rejected sender` … `participant=…` | Add his real digits to `NUMBERS` (e.g. `46704098198`) |
| `Processing capture` | Allowlist OK — check WAHA send / session WORKING |
| No lines | Webhook not firing — session/webhook |

## Behaviour

| Who / where | monsoon |
|-------------|---------|
| You → Message yourself | Your tasks |
| Anyone allowlisted → Todo group | Their own task user; reply in the group |
| You → typing in Todo | Ignored (`from_me_peer`) so family chat stays human |

## Smoke

In **Todo**, from his phone:

```text
help
todo call salon car detailing
list today
```
