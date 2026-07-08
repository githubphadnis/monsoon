# OpenCode offload brief — <task title>

> Paste everything from **Guardrails** down into **OpenCode Desktop** with the correct worktree open.
> Process: `docs/parallel-work.md`. **Do not commit or push.**

## Guardrails (always)

- Repo: `C:/projects/monsoon-<worktree>` (e.g. `monsoon-oc01`) · Branch: `<branch>` · **DO NOT commit or push.**
- Follow `AGENTS.md` → `CODING_GUIDELINES.md` → `agent_rules.md`.
- **Exclusive files only** — if you need another file, **stop and list it as a blocker**.
- **No secrets** — no `.env`, API keys, production hostnames with credentials.
- Match existing style: type hints, pytest, minimal diff.

## Goal

<one sentence: what done looks like>

## Read first

<exact paths>

## Do

1. <step>
2. <step>

## Constraints

<off-limits files; interfaces to implement exactly>

## Output

- [ ] Files created/edited: `<paths>`
- [ ] **Coverage metadata:** what was read/built, open questions
- [ ] All checklist items answered or marked **not covered**

## Completeness checklist

- [ ] <question 1>
- [ ] <question 2>

## Acceptance criteria

- [ ] `pytest <test path> -q` passes
- [ ] `git diff --name-only` touches **only** exclusive files (+ this brief if you tick boxes)
- [ ] No imports from files outside your track's contract
