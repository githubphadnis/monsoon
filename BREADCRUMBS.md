# BREADCRUMBS — monsoon

**Updated:** 2026-07-12

## Done

- Ephemeral WA cleanup (auto-delete replies + commands after TTL)
- Personal digests isolated; shared family chats; Ollama Auto routing
- Docs: per-person private channels (1:1 with monsoon number)

## Operator

1. Redeploy `main`.
2. Wife/son: each opens **1:1 with monsoon number** (not Message yourself on their phone).
3. Allowlist their `<digits>@c.us` in `ALLOWED_WHATSAPP_CHAT_IDS` + numbers.
4. Ephemeral defaults on (5 min). Override: `MONSOON_EPHEMERAL_SECONDS=300` or `0` to disable.
5. Optional: `OLLAMA_MODEL_CHAT=qwen2.5:14b` + pull on lenai.

## Branch

- `main`
