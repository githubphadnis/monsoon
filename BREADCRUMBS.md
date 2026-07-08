# BREADCRUMBS — monsoon

**Updated:** 2026-07-08 07:36

## WA pilot — DONE

5 chats, 91 messages indexed on notcoolio (`prakalp` session). Backfill fix deployed (`dac7ce6`).

## Next action

WhatsApp self-chat smoke on notcoolio stack:

1. `digest` — should use Ollama + WA context (or SQL fallback if lenai down)
2. `reflect <topic>` — pick a topic from your indexed chats
3. `todo smoke test` — capture still works
4. Optional: set `WORKFLOWY_API_KEY` + `WORKFLOWY_ROOT_NODE_ID` in Portainer for mirror

## Defer

- Full WA backfill (`--full`) until volume hardening
- Gmail OAuth

## Branch

- `main` @ `dac7ce6` — CI + GHCR green
