#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


import json
from packages.supervisor.common.db import connect
from packages.supervisor.common.ids import new_run_id
from packages.supervisor.common.prompt_registry import ensure_default_prompts

ensure_default_prompts()
with connect() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT outcome_status, count(*) FROM recommendation_outcomes GROUP BY outcome_status")
        counts = dict(cur.fetchall())
        total = sum(counts.values()) or 1
        positive_rate = counts.get('positive', 0) / total
        cur.execute('DELETE FROM calibration_metrics')
        cur.execute('INSERT INTO calibration_metrics (metric_name, metric_value, metric_json, updated_at) VALUES (%s,%s,%s,now())', ('positive_rate', positive_rate, json.dumps(counts)))
        cur.execute('INSERT INTO model_runs (model_run_id, cycle_id, run_kind, model_name, summary_json, created_at) VALUES (%s,(select cycle_id from market_state_cycles order by created_at desc limit 1),%s,%s,%s,now())', (f'modelrun_{new_run_id()}', 'calibration', 'deterministic-phase4', json.dumps({'counts': counts, 'positive_rate': positive_rate})))
        print(json.dumps({'ok': True, 'counts': counts, 'positive_rate': positive_rate}, ensure_ascii=False))
