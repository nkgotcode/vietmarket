#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from packages.supervisor.common.db import connect
from packages.supervisor.common.ids import new_failure_id, new_run_id
from packages.supervisor.common.time import utc_now
from packages.supervisor.health.failure_writer import write_failure
from packages.supervisor.health.worker_run_writer import write_worker_run
from packages.supervisor.signals.catalyst import build_catalyst_signals
from packages.supervisor.signals.common import load_latest_signal_context, replace_family_scores, upsert_default_policy
from packages.supervisor.signals.fundamentals import build_fundamental_signals
from packages.supervisor.signals.liquidity import build_liquidity_signals
from packages.supervisor.signals.momentum import build_momentum_signals
from packages.supervisor.signals.risk import build_risk_signals
from packages.supervisor.signals.trend import build_trend_signals

FAMILY_BUILDERS = {
    'trend': build_trend_signals,
    'momentum': build_momentum_signals,
    'catalyst': build_catalyst_signals,
    'fundamentals': build_fundamental_signals,
    'liquidity': build_liquidity_signals,
    'risk': build_risk_signals,
}


def build_signals() -> dict:
    with connect() as conn:
        context = load_latest_signal_context(conn)
        upsert_default_policy(conn)
        family_counts: dict[str, int] = {}
        preview: dict[str, list[dict]] = {}
        total_rows = 0
        total_components = 0
        for family, builder in FAMILY_BUILDERS.items():
            rows = builder(context)
            replace_family_scores(conn, cycle_id=context.cycle_id, family=family, rows=rows)
            family_counts[family] = len(rows)
            total_rows += len(rows)
            total_components += sum(len(row.get('components') or []) for row in rows)
            preview[family] = [
                {
                    'ticker': row['ticker'],
                    'score_normalized': row['score_normalized'],
                    'confidence': row['confidence'],
                    'blocking_flag': row['blocking_flag'],
                }
                for row in sorted(rows, key=lambda item: (item['score_normalized'], item['confidence']), reverse=True)[:5]
            ]
        return {
            'ok': True,
            'cycle_id': context.cycle_id,
            'family_counts': family_counts,
            'signal_score_count': total_rows,
            'signal_component_count': total_components,
            'preview': preview,
        }


if __name__ == '__main__':
    run_id = new_run_id()
    started_at = utc_now()
    try:
        result = build_signals()
        finished_at = utc_now()
        write_worker_run(
            run_id=run_id,
            job_name='supervisor_build_signals',
            dataset_name='signal_engine',
            status='complete',
            started_at=started_at,
            finished_at=finished_at,
            rows_written=result.get('signal_score_count', 0) + result.get('signal_component_count', 0),
            rows_upserted=result.get('signal_score_count', 0) + result.get('signal_component_count', 0),
            summary_json=result,
        )
        print(json.dumps(result, default=str, ensure_ascii=False))
    except Exception as exc:
        finished_at = utc_now()
        write_worker_run(
            run_id=run_id,
            job_name='supervisor_build_signals',
            dataset_name='signal_engine',
            status='failed',
            started_at=started_at,
            finished_at=finished_at,
            errors_count=1,
            summary_json={'error': str(exc)},
        )
        write_failure(
            failure_id=new_failure_id(),
            run_id=run_id,
            job_name='supervisor_build_signals',
            stage='build_signals',
            error_class=type(exc).__name__,
            error_message=str(exc),
            retryable=False,
        )
        raise
