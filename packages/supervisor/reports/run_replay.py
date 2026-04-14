#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


import json
from packages.supervisor.common.db import connect
from packages.supervisor.common.ids import new_run_id
from packages.supervisor.common.time import utc_now

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute('SELECT cycle_id FROM market_state_cycles ORDER BY created_at DESC LIMIT 1')
        row = cur.fetchone()
        if not row:
            raise SystemExit('no_market_state_cycle')
        cycle_id = row[0]
        replay_run_id = f'replay_{new_run_id()}'
        cur.execute('INSERT INTO replay_runs (replay_run_id, cycle_id, replay_scope, summary_json, created_at) VALUES (%s,%s,%s,%s,%s)', (replay_run_id, cycle_id, 'latest_cycle', json.dumps({'source': 'phase7_replay'}), utc_now()))
        cur.execute('SELECT ticker, total_score, ranking_bucket FROM candidate_rankings WHERE cycle_id = %s ORDER BY total_score DESC, ticker ASC LIMIT 20', (cycle_id,))
        rows = cur.fetchall()
        for ticker, total_score, ranking_bucket in rows:
            cur.execute('INSERT INTO replay_results (replay_run_id, ticker, result_json, created_at) VALUES (%s,%s,%s,%s)', (replay_run_id, ticker, json.dumps({'total_score': total_score, 'ranking_bucket': ranking_bucket}), utc_now()))
        print(json.dumps({'ok': True, 'replay_run_id': replay_run_id, 'cycle_id': cycle_id, 'count': len(rows)}, ensure_ascii=False))
