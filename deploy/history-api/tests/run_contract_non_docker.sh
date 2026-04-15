#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
OUT_DIR="$ROOT/deploy/status"
mkdir -p "$OUT_DIR"

BASE_URL="${CONTRACT_BASE_URL:-http://127.0.0.1:18787}"
API_KEY="${CONTRACT_API_KEY:-test-key}"
PG_URL="${CONTRACT_PG_URL:-postgres://vietmarket:vietmarket@100.83.150.39:5433/vietmarket?sslmode=disable}"

SERVER_LOG="$OUT_DIR/checkpoint-a-server.log"
VERIFY_LOG="$OUT_DIR/checkpoint-a-verify.log"
ENDPOINT_DIR="$OUT_DIR/checkpoint-a-endpoints"
mkdir -p "$ENDPOINT_DIR"

: > "$SERVER_LOG"
: > "$VERIFY_LOG"

cleanup() {
  if [[ -n "${SPID:-}" ]] && kill -0 "$SPID" 2>/dev/null; then
    kill "$SPID" || true
    sleep 1
    kill -9 "$SPID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

(
  cd "$ROOT/deploy/history-api"
  PORT=18787 API_KEY="$API_KEY" PG_URL="$PG_URL" node server.mjs
) > "$SERVER_LOG" 2>&1 &
SPID=$!

for i in $(seq 1 80); do
  if curl -fsS "$BASE_URL/healthz" >/dev/null 2>&1; then
    break
  fi
  sleep 0.25
done

if ! curl -fsS "$BASE_URL/healthz" >/dev/null 2>&1; then
  echo "FAIL healthz not ready" | tee -a "$VERIFY_LOG"
  exit 1
fi

echo "healthz: PASS" | tee -a "$VERIFY_LOG"

pass_count=0
fail_count=0

check_endpoint() {
  local name="$1"
  local path="$2"
  local outfile="$ENDPOINT_DIR/${name}.json"
  local status
  status=$(curl -sS -o "$outfile" -w "%{http_code}" -H "x-api-key: $API_KEY" "$BASE_URL$path")
  if [[ "$status" != "200" ]]; then
    echo "$name: FAIL status=$status" | tee -a "$VERIFY_LOG"
    fail_count=$((fail_count+1)); return
  fi
  if python3 - "$outfile" <<'PY'
import json,sys
p=sys.argv[1]
j=json.load(open(p))
ok = j.get('ok') is True and j.get('version')=='v1' and 'data' in j
sys.exit(0 if ok else 1)
PY
  then
    echo "$name: PASS status=200 envelope_ok=true" | tee -a "$VERIFY_LOG"
    pass_count=$((pass_count+1))
  else
    echo "$name: FAIL envelope invalid" | tee -a "$VERIFY_LOG"
    fail_count=$((fail_count+1))
  fi
}

check_endpoint analytics_overview "/v1/analytics/overview"
check_endpoint context_vcb "/v1/context/VCB"
check_endpoint sentiment_overview "/v1/sentiment/overview?windowDays=7&limit=5"
check_endpoint sentiment_vcb "/v1/sentiment/VCB?windowDays=30"
check_endpoint overall_health "/v1/overall/health"

# Error-contract checks
ua_status=$(curl -sS -o "$ENDPOINT_DIR/unauthorized.json" -w "%{http_code}" "$BASE_URL/v1/context/VCB")
if [[ "$ua_status" == "401" ]] && python3 - <<'PY'
import json
j=json.load(open('deploy/status/checkpoint-a-endpoints/unauthorized.json'))
assert j.get('error')=='unauthorized'
PY
then
  echo "unauthorized_contract: PASS" | tee -a "$VERIFY_LOG"
  pass_count=$((pass_count+1))
else
  echo "unauthorized_contract: FAIL status=$ua_status" | tee -a "$VERIFY_LOG"
  fail_count=$((fail_count+1))
fi

bad_status=$(curl -sS -o "$ENDPOINT_DIR/invalid_ticker.json" -w "%{http_code}" -H "x-api-key: $API_KEY" "$BASE_URL/v1/context/%40%40%40")
if [[ "$bad_status" == "400" ]] && python3 - <<'PY'
import json
j=json.load(open('deploy/status/checkpoint-a-endpoints/invalid_ticker.json'))
assert j.get('error')=='invalid_ticker'
PY
then
  echo "invalid_ticker_contract: PASS" | tee -a "$VERIFY_LOG"
  pass_count=$((pass_count+1))
else
  echo "invalid_ticker_contract: FAIL status=$bad_status" | tee -a "$VERIFY_LOG"
  fail_count=$((fail_count+1))
fi

win_status=$(curl -sS -o "$ENDPOINT_DIR/invalid_window.json" -w "%{http_code}" -H "x-api-key: $API_KEY" "$BASE_URL/v1/sentiment/overview?windowDays=0")
if [[ "$win_status" == "400" ]] && python3 - <<'PY'
import json
j=json.load(open('deploy/status/checkpoint-a-endpoints/invalid_window.json'))
assert j.get('error')=='invalid_window_days'
PY
then
  echo "invalid_window_contract: PASS" | tee -a "$VERIFY_LOG"
  pass_count=$((pass_count+1))
else
  echo "invalid_window_contract: FAIL status=$win_status" | tee -a "$VERIFY_LOG"
  fail_count=$((fail_count+1))
fi

echo "summary: pass=$pass_count fail=$fail_count" | tee -a "$VERIFY_LOG"
[[ "$fail_count" -eq 0 ]]
