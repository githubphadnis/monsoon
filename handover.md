# Handover — monsoon

## Last worked on

2026-07-15 — Personal ask/reflect use person-scoped WhatsApp corpus; WA index catch-up done.

## Current state / WIP

- Multi-session WAHA, ephemeral deletes, topic-scoped reflect, quiet acks — on `main`.
- Personal `ask` / `reflect` → tasks + `## Your WhatsApp` (person's WAHA session).
- Digests stay tasks-only. Gmail sync paused until refresh token re-auth.
- Operator: indexing complete for prakalp / Rashmi / Prathamesh; redeployed.

## Operator priorities

1. Smoke personal ask/reflect on a known indexed topic.
2. Optional: Gmail OAuth re-run when email in digests is wanted again.
3. Product next: WorkFlowy per-person + TASK vs CONTEXT depth gate.

## Next product work

- WorkFlowy: per-person roots; TASK vs CONTEXT; optional LLM “promote deeper?”
- MS-10 assign notify ([#9](https://github.com/githubphadnis/monsoon/issues/9))
- Gmail re-auth

## Environment

| Host | Role |
|------|------|
| `notcoolio` | monsoon Portainer stack |
| `lenai` | Ollama |
