#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="$ROOT/ops/logs/healthcheck.log"
COUNTER_FILE="$ROOT/ops/logs/.healthcheck_fail_count"
MAX_FAIL=3

mkdir -p "$ROOT/ops/logs"
log() { echo "[$(date -Is)] $*" >> "$LOG"; }

count=$(cat "$COUNTER_FILE" 2>/dev/null || echo 0)

if curl -sf --max-time 5 http://localhost:8000/healthz >/dev/null 2>&1; then
  echo 0 > "$COUNTER_FILE"
  exit 0
fi

count=$((count + 1))
echo "$count" > "$COUNTER_FILE"
log "healthcheck failed ($count/$MAX_FAIL)"

if [ "$count" -ge "$MAX_FAIL" ]; then
  log "restarting api + worker after $MAX_FAIL consecutive failures"
  cd "$ROOT" && docker compose restart api worker 2>&1 | while read -r line; do log "$line"; done
  echo 0 > "$COUNTER_FILE"
fi
