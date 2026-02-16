#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/lenamkhanh/vietmarket"
cd "$ROOT"

source "$ROOT/.venv/bin/activate"

CONVEX_URL="${CONVEX_URL:-${NEXT_PUBLIC_CONVEX_URL:-https://opulent-hummingbird-838.convex.cloud}}"
export CONVEX_URL

UNIVERSE_FILE="$ROOT/data/simplize/universe.latest.json"
CURSOR_FILE="${CURSOR_FILE:-$ROOT/tmp/vietmarket_candles_cursor.json}"
BATCH_SIZE="${BATCH_SIZE:-20}"
TFS="${TFS:-1d,1h,15m}"

python3 - <<'PY'
import json, os, subprocess, sys
from pathlib import Path
from datetime import datetime, timezone

root = Path('/Users/lenamkhanh/vietmarket')
universe_file = Path(os.environ.get('UNIVERSE_FILE', str(root/'data/simplize/universe.latest.json')))
batch_size = int(os.environ.get('BATCH_SIZE', '20'))
tfs = os.environ.get('TFS', '1d,1h,15m')

# Sharding + HA lease coordination
job_name = os.environ.get('JOB_NAME', 'candles')
node_id = os.environ.get('NODE_ID', 'unknown-node')
shard_count = int(os.environ.get('SHARD_COUNT', '12'))
shard_index = int(os.environ.get('SHARD_INDEX', '0'))
stale_minutes = int(os.environ.get('STALE_MINUTES', '30'))
lease_ms = int(os.environ.get('LEASE_MS', str(5*60_000)))

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

obj = json.loads(universe_file.read_text('utf-8'))
tickers_all = [t.strip().upper() for t in obj.get('tickers', []) if str(t).strip()]

include_indices = os.environ.get('INCLUDE_INDICES', '1') not in ('0','false','False','no','NO')
if include_indices:
    # Include VN indices.
    for x in ['VNINDEX','HNXINDEX','UPCOMINDEX']:
        if x not in tickers_all:
            tickers_all.append(x)

# Stable sharding by sha1(ticker)
import hashlib

def shard_of(t: str) -> int:
    h = hashlib.sha1(t.encode('utf-8')).hexdigest()
    return int(h[:8], 16) % max(shard_count, 1)

tickers = [t for t in tickers_all if shard_of(t) == (shard_index % max(shard_count, 1))]

import requests

def convex_mutation(path: str, args: dict, timeout_s: int = 20) -> dict:
    url = os.environ.get('CONVEX_URL', '').rstrip('/') + '/api/mutation'
    r = requests.post(url, json={'path': path, 'args': args}, timeout=timeout_s)
    r.raise_for_status()
    return r.json()

# Try to claim lease for this shard BEFORE doing any work.
try:
    if os.environ.get('CONVEX_URL'):
        lease = convex_mutation('leases:tryClaim', {
            'job': job_name,
            'shard': shard_index,
            'ownerId': node_id,
            'leaseMs': lease_ms,
            'staleMinutes': stale_minutes,
            'meta': f"boot shard_count={shard_count}",
        })
        val = lease.get('value', lease)
        if not (isinstance(val, dict) and val.get('ok')):
            print(json.dumps({'ok': True, 'skipped': 'not_owner', 'job': job_name, 'shard': shard_index, 'owner': val.get('ownerId') if isinstance(val, dict) else None}))
            sys.exit(0)
except Exception as e:
    print(json.dumps({'ok': True, 'skipped': 'lease_error', 'error': str(e)}))
    sys.exit(0)

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

# Wrap around
if len(sel) < batch_size and n > 0:
    sel += tickers[0 : (batch_size - len(sel))]

# Start dates (override via env per job)
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
    # Pass through INCLUDE_INDICES policy by adding a flag.
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
    if tf == '1d': run('1d', start_1d)
    elif tf == '1h': run('1h', start_1h)
    elif tf == '15m': run('15m', start_15m)
    else:
        raise SystemExit(f'Unsupported tf: {tf}')

def convex_mutation(path: str, args: dict, timeout_s: int = 20) -> dict:
    url = os.environ.get('CONVEX_URL', '').rstrip('/') + '/api/mutation'
    r = requests.post(url, json={'path': path, 'args': args}, timeout=timeout_s)
    r.raise_for_status()
    return r.json()

# Try to claim lease for this shard. If we can't, exit quietly.
try:
    import requests
    if os.environ.get('CONVEX_URL'):
        lease = convex_mutation('leases:tryClaim', {
            'job': job_name,
            'shard': shard_index,
            'ownerId': node_id,
            'leaseMs': lease_ms,
            'staleMinutes': stale_minutes,
            'meta': f"tickers_in_shard={n}",
        })
        val = lease.get('value', lease)
        if not (isinstance(val, dict) and val.get('ok')):
            # Not owner.
            print(json.dumps({'ok': True, 'skipped': 'not_owner', 'job': job_name, 'shard': shard_index, 'owner': val.get('ownerId') if isinstance(val, dict) else None}))
            sys.exit(0)
except Exception:
    # If lease fails (network), be safe: do nothing.
    print(json.dumps({'ok': True, 'skipped': 'lease_error'}))
    sys.exit(0)

next_index = (start + batch_size) % max(n, 1)
cur = {
    'updatedAt': datetime.now(timezone.utc).isoformat(timespec='seconds'),
    'nextIndex': next_index,
    'lastBatch': sel,
    'batchSize': batch_size,
    'universeCount': n,
}
cursor_file.parent.mkdir(parents=True, exist_ok=True)
cursor_file.write_text(json.dumps(cur, indent=2), encoding='utf-8')

# Report progress.
try:
    if os.environ.get('CONVEX_URL'):
        convex_mutation('leases:reportProgress', {
            'job': job_name,
            'shard': shard_index,
            'ownerId': node_id,
            'meta': f"nextIndex={next_index} last={sel[-1] if sel else ''}",
        })
except Exception:
    pass

print(json.dumps({'ok': True, 'selected': sel, 'nextIndex': next_index, 'universeCount': n, 'cursorFile': str(cursor_file), 'job': job_name, 'shard': shard_index, 'nodeId': node_id}, indent=2))
PY
