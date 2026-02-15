#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/lenamkhanh/vietmarket"
cd "$ROOT"

source "$ROOT/.venv/bin/activate"

CONVEX_URL="${CONVEX_URL:-${NEXT_PUBLIC_CONVEX_URL:-https://opulent-hummingbird-838.convex.cloud}}"
export CONVEX_URL

UNIVERSE_FILE="$ROOT/data/simplize/universe.latest.json"
CURSOR_FILE="$ROOT/tmp/vietmarket_candles_cursor.json"
BATCH_SIZE="${BATCH_SIZE:-20}"
TFS="${TFS:-1d,1h,15m}"

python3 - <<'PY'
import json, os, subprocess, sys
from pathlib import Path
from datetime import datetime, timezone

root = Path('/Users/lenamkhanh/vietmarket')
universe_file = Path(os.environ.get('UNIVERSE_FILE', str(root/'data/simplize/universe.latest.json')))
cursor_file = Path(os.environ.get('CURSOR_FILE', str(root/'tmp/vietmarket_candles_cursor.json')))
batch_size = int(os.environ.get('BATCH_SIZE', '20'))
tfs = os.environ.get('TFS', '1d,1h,15m')

obj = json.loads(universe_file.read_text('utf-8'))
tickers = [t.strip().upper() for t in obj.get('tickers', []) if str(t).strip()]

# Include VN indices.
for x in ['VNINDEX','HNXINDEX','UPCOMINDEX']:
    if x not in tickers:
        tickers.append(x)

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
    p = subprocess.run(cmd, cwd=str(root), env=os.environ.copy(), text=True)
    if p.returncode != 0:
        sys.exit(p.returncode)

for tf in [x.strip() for x in tfs.split(',') if x.strip()]:
    if tf == '1d': run('1d', start_1d)
    elif tf == '1h': run('1h', start_1h)
    elif tf == '15m': run('15m', start_15m)
    else:
        raise SystemExit(f'Unsupported tf: {tf}')

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

print(json.dumps({'ok': True, 'selected': sel, 'nextIndex': next_index, 'universeCount': n}, indent=2))
PY
