# BREADCRUMBS — monsoon

**Updated:** 2026-07-12

## Done

- MS-09 multi-session WAHA routing (`MONSOON_WAHA_SESSION_MAP`)
- Family roster, @assign, delete, ephemeral, Ollama Auto

## Operator (true Message yourself)

1. Pull/redeploy `main`.
2. WAHA dashboard: create sessions `prakalp`, `rashmi`, `prathamesh` → QR each phone.
3. Portainer:
   ```
   WAHA_SESSION=prakalp
   MONSOON_WAHA_SESSION_MAP=918291882204:prakalp,918291882206:rashmi,46704098198:prathamesh,918291884406:prathamesh
   ```
   + allowlists / aliases / shared group from `docs/family-model.md`
4. Smoke: each person `help` in Message yourself; family group still on Prakalp session.
5. `/health/ready` → `waha_sessions` lists all three.

## Branch

- `main`
