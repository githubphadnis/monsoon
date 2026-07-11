# BREADCRUMBS — monsoon

**Updated:** 2026-07-10 (evening)

## Done

- Family/peer 1:1: fix inbound `@lid` → phone via `remoteJidAlt`; ignore dad `from_me` in son's chat
- Docs: `docs/family-chat.md`
- Earlier: ask path, quieter digests, WorkFlowy notes

## Operator

1. Push/redeploy this fix (LID + from_me_peer).
2. Portainer env must list **both** your and son's phone in NUMBERS **and** CHAT_IDS.
3. Son sends `help` in your 1:1; watch logs for `Processing capture` vs `chat_not_allowed`.
4. See `docs/family-chat.md`.

## Branch

- `main` — commit/push when ready
