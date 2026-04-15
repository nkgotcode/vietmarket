#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from packages.supervisor.common.db import connect
from packages.supervisor.common.ids import new_failure_id, new_outcome_id, new_run_id
from packages.supervisor.common.time import utc_now
from packages.supervisor.evaluation.common import execute_values, json_dumps
from packages.supervisor.health.failure_writer import write_failure
from packages.supervisor.health.worker_run_writer import write_worker_run

HORIZONS = (1, 3, 5, 10, 20)
BENCHMARK_TICKER = 'VNINDEX'


def _close_at_or_before(cur, ticker: str, anchor_ts_ms: int) -> tuple[int, float] | None:
    cur.execute(
        '''
        SELECT ts, c
        FROM candles
        WHERE ticker = %s AND tf = '1d' AND ts <= %s
        ORDER BY ts DESC
        LIMIT 1
        ''',
        (ticker, anchor_ts_ms),
    )
    row = cur.fetchone()
    return (int(row[0]), float(row[1])) if row and row[1] is not None else None


def _future_window(cur, ticker: str, entry_ts_ms: int, horizon_days: int) -> list[tuple[int, float]]:
    cur.execute(
        '''
        SELECT ts, c
        FROM candles
        WHERE ticker = %s AND tf = '1d' AND ts > %s AND c IS NOT NULL
        ORDER BY ts ASC
        LIMIT %s
        ''',
        (ticker, entry_ts_ms, horizon_days),
    )
    return [(int(row[0]), float(row[1])) for row in cur.fetchall() if row[1] is not None]


def build_forward_labels() -> dict:
    rows_written = 0
    recommendation_rows = 0
    preview: list[dict[str, object]] = []
    latest_cycle_id = None
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT r.recommendation_id,
                       r.cycle_id,
                       r.ticker,
                       (extract(epoch from c.created_at) * 1000)::bigint,
                       ts.price_last,
                       ts.liquidity_bucket,
                       ts.sector,
                       m.market_regime
                FROM recommendations r
                JOIN market_state_cycles c ON c.cycle_id = r.cycle_id
                LEFT JOIN ticker_snapshots ts ON ts.cycle_id = r.cycle_id AND ts.ticker = r.ticker
                LEFT JOIN market_regime_snapshots m ON m.cycle_id = r.cycle_id
                ORDER BY c.created_at DESC, r.ticker ASC
                '''
            )
            recommendation_inputs = cur.fetchall()
            recommendation_rows = len(recommendation_inputs)

            cur.execute('DELETE FROM ticker_forward_outcomes')
            payload = []
            latest_cycle_id = recommendation_inputs[0][1] if recommendation_inputs else None

            for recommendation_id, cycle_id, ticker, cycle_ts_ms, price_last, liquidity_bucket, sector, market_regime in recommendation_inputs:
                cycle_ts_ms = int(cycle_ts_ms)
                entry = _close_at_or_before(cur, ticker, cycle_ts_ms)
                benchmark_entry = _close_at_or_before(cur, BENCHMARK_TICKER, cycle_ts_ms)
                had_daily_entry = entry is not None
                if entry is None and price_last is not None:
                    entry = (cycle_ts_ms, float(price_last))
                if entry is None:
                    continue

                entry_ts, entry_price = entry
                benchmark_entry_ts = benchmark_entry[0] if benchmark_entry else None
                benchmark_entry_price = benchmark_entry[1] if benchmark_entry else None

                for horizon_days in HORIZONS:
                    future_window = _future_window(cur, ticker, entry_ts, horizon_days)
                    benchmark_window = _future_window(cur, BENCHMARK_TICKER, benchmark_entry_ts or entry_ts, horizon_days)

                    exit_ts = future_window[-1][0] if len(future_window) >= horizon_days else None
                    exit_price = future_window[-1][1] if len(future_window) >= horizon_days else None
                    benchmark_exit_ts = benchmark_window[-1][0] if len(benchmark_window) >= horizon_days else None
                    benchmark_exit_price = benchmark_window[-1][1] if len(benchmark_window) >= horizon_days else None

                    forward_return = ((exit_price / entry_price) - 1.0) if exit_price is not None and entry_price else None
                    benchmark_return = ((benchmark_exit_price / benchmark_entry_price) - 1.0) if benchmark_exit_price is not None and benchmark_entry_price else None
                    excess_return = (forward_return - benchmark_return) if forward_return is not None and benchmark_return is not None else None

                    path_closes = [close for _, close in future_window[:horizon_days]]
                    max_drawdown = ((min(path_closes) / entry_price) - 1.0) if path_closes and entry_price else None
                    max_favorable_excursion = ((max(path_closes) / entry_price) - 1.0) if path_closes and entry_price else None

                    label_json = {
                        'available_bars': len(future_window),
                        'benchmark_available_bars': len(benchmark_window),
                        'entry_source': 'daily_candle' if had_daily_entry else 'ticker_snapshot_price_last',
                        'benchmark_ticker': BENCHMARK_TICKER,
                    }
                    payload.append(
                        (
                            new_outcome_id(),
                            recommendation_id,
                            cycle_id,
                            ticker,
                            horizon_days,
                            entry_ts,
                            exit_ts,
                            BENCHMARK_TICKER,
                            entry_price,
                            exit_price,
                            benchmark_entry_price,
                            benchmark_exit_price,
                            forward_return,
                            benchmark_return,
                            excess_return,
                            max_drawdown,
                            max_favorable_excursion,
                            liquidity_bucket,
                            sector,
                            market_regime,
                            json.dumps(label_json, default=str),
                            utc_now(),
                        )
                    )
                    if horizon_days == 5 and len(preview) < 10:
                        preview.append(
                            {
                                'cycle_id': cycle_id,
                                'ticker': ticker,
                                'forward_return_5d': forward_return,
                                'excess_return_5d': excess_return,
                                'available_bars': len(future_window),
                            }
                        )

            execute_values(
                cur,
                '''
                INSERT INTO ticker_forward_outcomes (
                  outcome_id, recommendation_id, cycle_id, ticker, horizon_days,
                  entry_ts, exit_ts, benchmark_ticker, entry_price, exit_price,
                  benchmark_entry_price, benchmark_exit_price, forward_return, benchmark_return,
                  excess_return, max_drawdown, max_favorable_excursion, liquidity_bucket,
                  sector, market_regime, label_json, created_at
                ) VALUES %s
                ''',
                payload,
            )
            rows_written = len(payload)

    return {
        'ok': True,
        'latest_cycle_id': latest_cycle_id,
        'recommendation_count': recommendation_rows,
        'horizons': list(HORIZONS),
        'rows_written': rows_written,
        'preview': preview,
    }


if __name__ == '__main__':
    run_id = new_run_id()
    started_at = utc_now()
    try:
        result = build_forward_labels()
        finished_at = utc_now()
        write_worker_run(
            run_id=run_id,
            job_name='supervisor_build_forward_labels',
            dataset_name='ticker_forward_outcomes',
            status='complete',
            started_at=started_at,
            finished_at=finished_at,
            rows_written=result.get('rows_written', 0),
            rows_upserted=result.get('rows_written', 0),
            summary_json=result,
        )
        print(json_dumps(result))
    except Exception as exc:
        finished_at = utc_now()
        write_worker_run(
            run_id=run_id,
            job_name='supervisor_build_forward_labels',
            dataset_name='ticker_forward_outcomes',
            status='failed',
            started_at=started_at,
            finished_at=finished_at,
            errors_count=1,
            summary_json={'error': str(exc)},
        )
        write_failure(
            failure_id=new_failure_id(),
            run_id=run_id,
            job_name='supervisor_build_forward_labels',
            stage='build_forward_labels',
            error_class=type(exc).__name__,
            error_message=str(exc),
            retryable=False,
        )
        raise
