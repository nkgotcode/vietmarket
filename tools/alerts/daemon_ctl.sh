#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PIDFILE="$ROOT/runtime/alerts/daemon.pid"
LOGFILE="$ROOT/runtime/alerts/daemon.log"

PG_URL_DEFAULT="postgres://vietmarket:vietmarket@100.83.150.39:5433/vietmarket?sslmode=disable"
PG_URL="${PG_URL:-$PG_URL_DEFAULT}"

start() {
  mkdir -p "$ROOT/runtime/alerts"
  if [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    echo "daemon already running pid=$(cat "$PIDFILE")"
    exit 0
  fi
  cd "$ROOT"
  nohup .venv/bin/python tools/alerts/run_alert_daemon.py \
    --pg-url "$PG_URL" \
    --rules config/alerts/rules.v1.yaml \
    --watchlists config/alerts/watchlists.json \
    --portfolio config/alerts/portfolio_symbols_current.json \
    --channels config/alerts/channels.json \
    --state runtime/alerts/state.json \
    --firelog runtime/alerts/fires.jsonl \
    >> "$LOGFILE" 2>&1 &
  echo $! > "$PIDFILE"
  echo "started pid=$(cat "$PIDFILE")"
}

stop() {
  if [[ -f "$PIDFILE" ]]; then
    PID="$(cat "$PIDFILE")"
    kill "$PID" 2>/dev/null || true
    rm -f "$PIDFILE"
    echo "stopped pid=$PID"
  else
    echo "not running"
  fi
}

status() {
  if [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    echo "running pid=$(cat "$PIDFILE")"
  else
    echo "stopped"
    exit 1
  fi
}

logs() {
  mkdir -p "$ROOT/runtime/alerts"
  touch "$LOGFILE"
  tail -n 200 -f "$LOGFILE"
}

case "${1:-}" in
  start) start ;;
  stop) stop ;;
  restart) stop; start ;;
  status) status ;;
  logs) logs ;;
  *) echo "usage: $0 {start|stop|restart|status|logs}"; exit 1 ;;
esac
