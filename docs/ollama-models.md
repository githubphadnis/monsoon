# Ollama models — monsoon

Monsoon talks to Ollama on **lenai**. You can run one model for everything, or
**Auto-style routing** by purpose (not Cursor-grade complexity scoring — simpler
and predictable).

## Modes

| Mode | Env | Behaviour |
|------|-----|-----------|
| Single | `OLLAMA_MODEL=…` only | Parse + digest/ask/reflect all use that model |
| Auto | also set `OLLAMA_MODEL_PARSE` and/or `OLLAMA_MODEL_CHAT` | Route by purpose |

| Purpose | Used for | Prefer |
|---------|----------|--------|
| **parse** | Intent JSON (`todo` vs `ask` when LLM parse is used) | Small/fast (coder or 3–8B) |
| **chat** | `digest`, `reflect`, free-text `ask` | Larger instruct / chat model |

Empty role override → falls back to `OLLAMA_MODEL`.

## Recommended starter (depth over speed)

On **lenai**:

```bash
ollama pull qwen2.5:14b          # or llama3.1:8b / mistral-nemo / gemma2:9b
ollama pull qwen2.5-coder:7b     # keep as fast parser (optional)
ollama list
```

Portainer:

```env
OLLAMA_MODEL=qwen2.5:14b
OLLAMA_MODEL_PARSE=qwen2.5-coder:7b
OLLAMA_MODEL_CHAT=qwen2.5:14b
OLLAMA_TIMEOUT_SECONDS=60
OLLAMA_CHAT_TIMEOUT_SECONDS=180
```

If VRAM is tight, try `qwen2.5:7b` or `llama3.1:8b` for chat instead of 14b.

**Avoid** coder-only models for chat — they write stiff, tool-like prose.

## Verify

After recreate, `GET /health/ready` shows:

- `ollama_model` / `ollama_model_parse` / `ollama_model_chat`
- `ollama_routing_active: true` when overrides are set

Smoke on WhatsApp: `digest` and a free-text question — expect warmer, more specific replies (and slightly longer wait).
