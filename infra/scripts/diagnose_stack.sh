#!/usr/bin/env bash
# Run on notcoolio to debug WAHA → monsoon webhook path.
set -euo pipefail

API_KEY="${WAHA_API_KEY:-Monsoon2026!}"
SESSION="${WAHA_SESSION:-prakalp}"
WAHA_URL="${WAHA_BASE_URL:-http://127.0.0.1:13000}"

APP_CTN=$(docker ps --format '{{.Names}}' | grep -E 'monsoon.*app|_app_' | head -1 || true)
WAHA_CTN=$(docker ps --format '{{.Names}}' | grep -E 'monsoon.*waha|_waha_' | head -1 || true)

echo "=== Containers ==="
echo "app:  ${APP_CTN:-NOT FOUND}"
echo "waha: ${WAHA_CTN:-NOT FOUND}"

echo
echo "=== App health (host) ==="
curl -sS "http://127.0.0.1:8080/health/live" || echo "FAIL"
echo
curl -sS "http://127.0.0.1:8080/health/db" || echo "FAIL"
echo
curl -sS "http://127.0.0.1:8080/health/webhook" || echo "FAIL"
echo

if [[ -n "${WAHA_CTN}" ]]; then
  echo "=== WAHA → app DNS (from waha container) ==="
  docker exec "$WAHA_CTN" sh -c 'curl -sS -m 5 http://app:8080/health/live || echo app: FAIL'
  echo
  docker exec "$WAHA_CTN" sh -c 'curl -sS -m 5 http://monsoon-app:8080/health/live || echo monsoon-app: FAIL'
  echo
fi

echo "=== Session webhook config ==="
curl -sS -H "X-Api-Key: ${API_KEY}" "${WAHA_URL}/api/sessions/${SESSION}" | python3 -m json.tool 2>/dev/null | head -40 || \
  curl -sS -H "X-Api-Key: ${API_KEY}" "${WAHA_URL}/api/sessions/${SESSION}"

if [[ -n "${APP_CTN}" && -n "${WAHA_CTN}" ]]; then
  APP_IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$APP_CTN")
  echo
  echo "=== Manual webhook POST (from waha → app) ==="
  docker exec "$WAHA_CTN" sh -c "curl -sS -m 10 -X POST http://monsoon-app:8080/api/webhooks/waha \
    -H 'Content-Type: application/json' \
    -H 'X-Api-Key: ${API_KEY}' \
    -d '{\"event\":\"message.any\",\"session\":\"${SESSION}\",\"me\":{\"id\":\"918291882204@c.us\"},\"payload\":{\"id\":\"diag_manual_$(date +%s)\",\"from\":\"29304595423273@lid\",\"fromMe\":true,\"body\":\"todo diagnose webhook\",\"_data\":{\"key\":{\"remoteJidAlt\":\"918291882204@s.whatsapp.net\"}}}}'"
  echo
  echo "If that returned {\"status\":\"ok\"} but no WhatsApp reply, check app logs."
  echo "If app: FAIL above, re-wire webhook to: http://${APP_IP}:8080/api/webhooks/waha"
fi

if [[ -n "${APP_CTN}" ]]; then
  echo
  echo "=== App logs (last 30 lines) ==="
  docker logs "$APP_CTN" --tail 30 2>&1
fi
