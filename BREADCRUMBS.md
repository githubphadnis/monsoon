# BREADCRUMBS — monsoon

**Updated:** 2026-07-08 08:40

## Done this session

- Roadmap reordered; GH issues [#1–#8](https://github.com/githubphadnis/monsoon/issues) + milestones V1.0 / V1.1
- MS-01 code: email lines in context slice (`digest` / `reflect` get `## Email` section)
- Title-first LLM replies pushed (`c762e3a`)

## Next action (operator — MS-01)

1. On PC: `python infra/scripts/gmail_oauth_setup.py --client-secrets …` → copy refresh token
2. Portainer: set `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN` (omit `GMAIL_SYNC_MAX_PAGES` or leave empty)
3. Redeploy stack
4. On notcoolio:
   - `curl -s http://127.0.0.1:8080/health/gmail-index | python3 -m json.tool`
   - `docker exec monsoon-app python infra/scripts/gmail_sync.py --max-pages 2`
5. WhatsApp: `reflect <topic from inbox>` — should cite email + WA

## Then (code)

- **#2** MS-02 WorkFlowy reverse sync
- **#3** MS-03 scheduled cron

## Branch

- `main` — push pending this session
