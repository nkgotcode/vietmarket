#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from packages.supervisor.common.db import connect
from packages.supervisor.common.ids import new_run_id
from packages.supervisor.common.prompt_registry import ensure_default_prompts

ensure_default_prompts()
with connect() as conn:
    with conn.cursor() as cur:
        cur.execute('DELETE FROM calibration_metrics')

        cur.execute(
            '''
            SELECT count(*)::int,
                   avg(CASE WHEN forward_return > 0 THEN 1.0 ELSE 0.0 END)::float8,
                   avg(forward_return)::float8,
                   avg(excess_return)::float8
            FROM ticker_forward_outcomes
            WHERE horizon_days = 5
              AND forward_return IS NOT NULL
            '''
        )
        sample_size, positive_rate, avg_forward_return, avg_excess_return = cur.fetchone()

        cur.execute(
            '''
            SELECT avg_forward_return
            FROM calibration_buckets
            WHERE calibration_run_id = (SELECT calibration_run_id FROM calibration_runs ORDER BY created_at DESC LIMIT 1)
              AND horizon_days = 5
              AND bucket_name IN ('score_decile_1', 'score_decile_10')
            ORDER BY bucket_name ASC
            '''
        )
        decile_rows = [row[0] for row in cur.fetchall()]
        top_bottom_spread = decile_rows[0] - decile_rows[1] if len(decile_rows) == 2 and None not in decile_rows else None

        cur.execute(
            '''
            SELECT count(*)::int
            FROM cohort_metrics
            WHERE cohort_type = 'market_regime' AND horizon_days = 5
            '''
        )
        regime_bucket_count = cur.fetchone()[0]

        metrics = [
            ('sample_size_5d', float(sample_size or 0), {'sample_size': int(sample_size or 0)}),
            ('positive_rate_5d', float(positive_rate or 0.0), {'horizon_days': 5}),
            ('avg_forward_return_5d', float(avg_forward_return or 0.0), {'horizon_days': 5}),
            ('avg_excess_return_5d', float(avg_excess_return or 0.0), {'horizon_days': 5}),
            ('top_bottom_spread_5d', float(top_bottom_spread or 0.0), {'horizon_days': 5}),
            ('regime_bucket_count_5d', float(regime_bucket_count or 0), {'horizon_days': 5}),
        ]

        for metric_name, metric_value, metric_json in metrics:
            cur.execute(
                'INSERT INTO calibration_metrics (metric_name, metric_value, metric_json, updated_at) VALUES (%s,%s,%s,now())',
                (metric_name, metric_value, json.dumps(metric_json)),
            )

        cur.execute(
            '''
            INSERT INTO model_runs (
              model_run_id, cycle_id, run_kind, model_name, summary_json, created_at
            ) VALUES (
              %s,
              (select cycle_id from market_state_cycles order by created_at desc limit 1),
              %s,
              %s,
              %s,
              now()
            )
            ''',
            (
                f'modelrun_{new_run_id()}',
                'calibration_v2',
                'legacy-phase3-eval-foundation',
                json.dumps(
                    {
                        'sample_size_5d': int(sample_size or 0),
                        'positive_rate_5d': float(positive_rate or 0.0),
                        'avg_forward_return_5d': float(avg_forward_return or 0.0),
                        'avg_excess_return_5d': float(avg_excess_return or 0.0),
                        'top_bottom_spread_5d': float(top_bottom_spread or 0.0),
                        'regime_bucket_count_5d': int(regime_bucket_count or 0),
                    }
                ),
            ),
        )

        print(
            json.dumps(
                {
                    'ok': True,
                    'sample_size_5d': int(sample_size or 0),
                    'positive_rate_5d': float(positive_rate or 0.0),
                    'avg_forward_return_5d': float(avg_forward_return or 0.0),
                    'avg_excess_return_5d': float(avg_excess_return or 0.0),
                    'top_bottom_spread_5d': float(top_bottom_spread or 0.0),
                    'regime_bucket_count_5d': int(regime_bucket_count or 0),
                },
                ensure_ascii=False,
            )
        )
