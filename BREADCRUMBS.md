# BREADCRUMBS — monsoon

**Updated:** 2026-07-12

## Done

- Personal digests isolated; `MONSOON_SHARED_CHAT_IDS` for family pooled space
- Ollama Auto routing: `OLLAMA_MODEL_PARSE` / `OLLAMA_MODEL_CHAT` (+ chat timeout)

## Operator

1. Pull/redeploy latest `main`.
2. On lenai: `ollama pull qwen2.5:14b` (or 8B if VRAM tight).
3. Portainer example:
   ```
   OLLAMA_MODEL=qwen2.5:14b
   OLLAMA_MODEL_PARSE=qwen2.5-coder:7b
   OLLAMA_MODEL_CHAT=qwen2.5:14b
   OLLAMA_CHAT_TIMEOUT_SECONDS=180
   MONSOON_SHARED_CHAT_IDS=120363143633935585@g.us
   ```
4. Smoke: son `digest` in Todo = his tasks only; family `list` = pooled; ask feels richer.

## Branch

- `main`
