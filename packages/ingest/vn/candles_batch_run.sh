#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"

# Use local venv if present (dev on mac mini). Containers won't have it.
if [ -f "$ROOT/.venv/bin/activate" ]; then
  source "$ROOT/.venv/bin/activate"
fi

# Timescale/Postgres is the only active runtime path.
export PG_URL="${PG_URL:-}"

# Provide a stable root path for embedded python.
export VIETMARKET_ROOT="$ROOT"

UNIVERSE_FILE="${UNIVERSE_FILE:-$ROOT/data/simplize/universe.latest.json}"
CURSOR_FILE="${CURSOR_FILE:-$ROOT/tmp/vietmarket_candles_cursor.json}"
BATCH_SIZE="${BATCH_SIZE:-20}"
TFS="${TFS:-1d,1h,15m}"

python3 - <<'PY'
import json, os, subprocess, sys
from pathlib import Path
from datetime import datetime, timezone

root = Path(os.environ.get('VIETMARKET_ROOT', '.')).resolve()
universe_file = Path(os.environ.get('UNIVERSE_FILE', str(root/'data/simplize/universe.latest.json')))
batch_size = int(os.environ.get('BATCH_SIZE', '20'))
tfs = os.environ.get('TFS', '1d,1h,15m')

# Sharding + cursor coordination.
job_name = os.environ.get('JOB_NAME', 'candles')
node_id = os.environ.get('NODE_ID', 'unknown-node')
shard_count = int(os.environ.get('SHARD_COUNT', '12'))
shard_index = int(os.environ.get('SHARD_INDEX', '0'))

# Cursor file: MUST be per-shard to avoid corruption when running SHARD_COUNT>1.
# - If CURSOR_FILE is set, use it.
# - Else if CURSOR_DIR is set, write ${CURSOR_DIR}/${JOB_NAME}_${SHARD_INDEX}.json
# - Else default to tmp/${JOB_NAME}_${SHARD_INDEX}.json
cursor_env = os.environ.get('CURSOR_FILE')
if cursor_env:
    cursor_file = Path(cursor_env)
else:
    cursor_dir = Path(os.environ.get('CURSOR_DIR', str(root/'tmp')))
    cursor_file = cursor_dir / f"{job_name}_{shard_index}.json"

universe_mode = os.environ.get('UNIVERSE_MODE', 'file').strip().lower()


def load_tickers_from_file():
    obj = json.loads(universe_file.read_text('utf-8'))
    return [t.strip().upper() for t in obj.get('tickers', []) if str(t).strip()]


def load_tickers_from_pg():
    import psycopg2
    pg_url = os.environ.get('PG_URL', '')
    if not pg_url:
        raise RuntimeError('UNIVERSE_MODE=pg requires PG_URL')
    where = os.environ.get('UNIVERSE_WHERE', "(active IS TRUE) OR (active IS NULL)")
    sql = f"SELECT ticker FROM symbols WHERE {where} ORDER BY ticker"
    with psycopg2.connect(pg_url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return [r[0].strip().upper() for r in cur.fetchall() if r and r[0]]


tickers_all = load_tickers_from_pg() if universe_mode == 'pg' else load_tickers_from_file()

# Filter universe down to VN equities only.
import re
VN_EQ_RE = re.compile(r'^[A-Z0-9]{3,4}$')


def is_vn_equity(sym: str) -> bool:
    if sym in ('VNINDEX', 'HNXINDEX', 'UPCOMINDEX'):
        return True
    return bool(VN_EQ_RE.match(sym))


tickers_all = [t for t in tickers_all if is_vn_equity(t)]

include_indices = os.environ.get('INCLUDE_INDICES', '1') not in ('0','false','False','no','NO')
if include_indices:
    for x in ['VNINDEX','HNXINDEX','UPCOMINDEX']:
        if x not in tickers_all:
            tickers_all.append(x)

import hashlib


def shard_of(t: str) -> int:
    h = hashlib.sha1(t.encode('utf-8')).hexdigest()
    return int(h[:8], 16) % max(shard_count, 1)


tickers = [t for t in tickers_all if shard_of(t) == (shard_index % max(shard_count, 1))]

# load cursor
cur = {'nextIndex': 0}
if cursor_file.exists():
    try:
        cur.update(json.loads(cursor_file.read_text('utf-8')))
    except Exception:
        pass

n = len(tickers)
start = int(cur.get('nextIndex', 0)) % max(n, 1)
end = min(start + batch_size, n)
sel = tickers[start:end]

if len(sel) < batch_size and n > 0:
    sel += tickers[0 : (batch_size - len(sel))]

start_1d = os.environ.get('START_1D', '2000-01-01')
start_1h = os.environ.get('START_1H', '2000-01-01')
start_15m = os.environ.get('START_15M', '2000-01-01')
run_timeout = int(os.environ.get('RUN_TIMEOUT_SEC', '300'))


def run(tf: str, start_date: str):
    cmd = [
        'python3',
        str(root/'packages/ingest/vn/candles_backfill.py'),
        '--tickers', ','.join(sel),
        '--tfs', tf,
        '--start', start_date,
        '--chunk', os.environ.get('CHUNK', '1200'),
        '--sleep', os.environ.get('SLEEP', '0.02'),
    ]
    if not include_indices:
        cmd.append('--exclude-indices')

    try:
        p = subprocess.run(cmd, cwd=str(root), env=os.environ.copy(), text=True, timeout=run_timeout)
    except subprocess.TimeoutExpired:
        print(json.dumps({'ok': False, 'error': 'run_timeout', 'tf': tf, 'timeoutSec': run_timeout, 'tickers': sel[:3]}))
        sys.exit(124)

    if p.returncode != 0:
        sys.exit(p.returncode)


for tf in [x.strip() for x in tfs.split(',') if x.strip()]:
    if tf == '1d':
        run('1d', start_1d)
    elif tf == '1h':
        run('1h', start_1h)
    elif tf == '15m':
        run('15m', start_15m)
    else:
        raise SystemExit(f'Unsupported tf: {tf}')

next_index = (start + batch_size) % max(n, 1)
cur = {
    'updatedAt': datetime.now(timezone.utc).isoformat(timespec='seconds'),
    'nextIndex': next_index,
    'lastBatch': sel,
    'batchSize': batch_size,
    'universeCount': n,
    'job': job_name,
    'shard': shard_index,
    'nodeId': node_id,
}
cursor_file.parent.mkdir(parents=True, exist_ok=True)
cursor_file.write_text(json.dumps(cur, indent=2), encoding='utf-8')

print(json.dumps({'ok': True, 'universeMode': universe_mode, 'universeWhere': os.environ.get('UNIVERSE_WHERE'), 'selected': sel, 'nextIndex': next_index, 'universeCount': n, 'cursorFile': str(cursor_file), 'job': job_name, 'shard': shard_index, 'nodeId': node_id}, indent=2))
PY
