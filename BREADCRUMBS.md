# BREADCRUMBS — monsoon

**Updated:** 2026-07-08 07:05

## Your only action

**WA backfill on notcoolio** (Phase 3):

```bash
curl -s http://127.0.0.1:8080/health/webhook | python3 -m json.tool
docker exec monsoon-app python infra/scripts/wa_backfill.py --max-chats 5
curl -s http://127.0.0.1:8080/health/wa-index | python3 -m json.tool
```

Report: `Phase 3 done` + wa-index JSON.

**Skip OpenCode** — Cursor shipped OC-01/02/03 + WorkFlowy on `feature/llm-phase-a`.

## Cursor state

- `feature/llm-phase-a` — LLM digest, reflect, context slice, WorkFlowy push, 58 tests pass
- Pending: commit, your WA pilot, deploy branch to notcoolio

## Smoke after deploy

- `digest`
- `reflect griham`
- `todo smoke test`
- `note 1 follow-up text` (if task #1 exists)
