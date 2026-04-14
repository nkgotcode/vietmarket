#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from packages.supervisor.common.db import connect
from packages.supervisor.common.ids import (
    new_failure_id,
    new_run_id,
    new_supervisor_run_id,
    new_supervisor_step_id,
)
from packages.supervisor.common.time import utc_now
from packages.supervisor.health.failure_writer import write_failure
from packages.supervisor.health.worker_run_writer import write_worker_run


@dataclass(frozen=True)
class StepDef:
    name: str
    script_path: str
    requires_healthy: bool = False


DAILY_STEPS: tuple[StepDef, ...] = (
    StepDef('build_freshness', 'packages/supervisor/health/build_freshness.py'),
    StepDef('build_system_health', 'packages/supervisor/health/build_system_health.py'),
    StepDef('build_market_state', 'packages/supervisor/snapshots/build_market_state.py'),
    StepDef('build_signals', 'packages/supervisor/signals/build_signals.py', requires_healthy=True),
    StepDef('rank_candidates', 'packages/supervisor/signals/rank_candidates.py', requires_healthy=True),
    StepDef('generate_theses', 'packages/supervisor/theses/generate_theses.py', requires_healthy=True),
    StepDef('generate_recommendations', 'packages/supervisor/recommendations/generate_recommendations.py', requires_healthy=True),
    StepDef('evaluate_policy', 'packages/supervisor/policy/engine.py', requires_healthy=True),
    StepDef('run_paper_portfolio', 'packages/supervisor/portfolio/paper_order_engine.py', requires_healthy=True),
    StepDef('generate_daily_brief', 'packages/supervisor/reports/generate_daily_brief.py', requires_healthy=True),
    StepDef('generate_decision_journal', 'packages/supervisor/reports/generate_decision_journal.py', requires_healthy=True),
    StepDef('dispatch_daily_brief', 'packages/supervisor/delivery/dispatch_daily_brief.py', requires_healthy=True),
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, default=str, ensure_ascii=False)


def _json_safe(payload: Any) -> Any:
    return json.loads(_json_dumps(payload))


def _extract_json(stdout: str) -> dict[str, Any] | None:
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    for line in reversed(lines):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
        return {'value': payload}
    return None


def _latest_health(conn) -> tuple[str | None, str | None]:
    with conn.cursor() as cur:
        cur.execute(
            'SELECT snapshot_id, overall_status FROM system_health_snapshots ORDER BY created_at DESC LIMIT 1'
        )
        row = cur.fetchone()
    if not row:
        return None, None
    return row[0], row[1]


def _latest_cycle(conn) -> str | None:
    with conn.cursor() as cur:
        cur.execute('SELECT cycle_id FROM market_state_cycles ORDER BY created_at DESC LIMIT 1')
        row = cur.fetchone()
    return row[0] if row else None


def _insert_run(supervisor_run_id: str, run_id: str, mode: str, strict_health_gate: bool, started_at) -> None:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO supervisor_runs (
                  supervisor_run_id, run_id, run_type, mode, requested_by, strict_health_gate,
                  nomad_job_id, nomad_alloc_id, status, summary_json, started_at, finished_at
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ''',
                (
                    supervisor_run_id,
                    run_id,
                    'manual' if not os.environ.get('NOMAD_JOB_NAME') else 'periodic',
                    mode,
                    os.environ.get('USER') or os.environ.get('LOGNAME'),
                    strict_health_gate,
                    os.environ.get('NOMAD_JOB_NAME'),
                    os.environ.get('NOMAD_ALLOC_ID'),
                    'running',
                    _json_dumps({'mode': mode, 'status': 'running'}),
                    started_at,
                    None,
                ),
            )


def _update_run(
    supervisor_run_id: str,
    *,
    status: str,
    latest_health_snapshot_id: str | None,
    latest_health_status: str | None,
    latest_cycle_id: str | None,
    summary: dict[str, Any],
    finished_at=None,
) -> None:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                UPDATE supervisor_runs
                   SET status = %s,
                       latest_health_snapshot_id = %s,
                       latest_health_status = %s,
                       latest_cycle_id = %s,
                       summary_json = %s,
                       finished_at = %s
                 WHERE supervisor_run_id = %s
                ''',
                (
                    status,
                    latest_health_snapshot_id,
                    latest_health_status,
                    latest_cycle_id,
                    _json_dumps(summary),
                    finished_at,
                    supervisor_run_id,
                ),
            )


def _insert_step(
    supervisor_run_id: str,
    *,
    step_name: str,
    step_order: int,
    script_path: str,
    status: str,
    raw_output: str,
    summary: dict[str, Any],
    started_at,
    finished_at,
) -> None:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO supervisor_run_steps (
                  supervisor_step_id, supervisor_run_id, step_name, step_order, script_path,
                  status, raw_output, summary_json, started_at, finished_at
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ''',
                (
                    new_supervisor_step_id(),
                    supervisor_run_id,
                    step_name,
                    step_order,
                    script_path,
                    status,
                    raw_output,
                    _json_dumps(summary),
                    started_at,
                    finished_at,
                ),
            )


def _run_step(step: StepDef) -> dict[str, Any]:
    started_at = utc_now()
    script_abs = repo_root() / step.script_path
    proc = subprocess.run(
        [sys.executable, str(script_abs)],
        cwd=repo_root(),
        env=os.environ.copy(),
        capture_output=True,
        text=True,
    )
    finished_at = utc_now()
    stdout = proc.stdout.strip()
    stderr = proc.stderr.strip()
    summary = _extract_json(stdout) or {}
    status = 'complete' if proc.returncode == 0 else 'failed'
    return {
        'step_name': step.name,
        'script_path': step.script_path,
        'status': status,
        'started_at': started_at,
        'finished_at': finished_at,
        'returncode': proc.returncode,
        'stdout': stdout,
        'stderr': stderr,
        'summary': summary,
        'requires_healthy': step.requires_healthy,
    }


def run_supervisor_cycle(mode: str = 'daily', strict_health_gate: bool = False) -> dict[str, Any]:
    if mode != 'daily':
        raise RuntimeError(f'unsupported_mode:{mode}')
    steps = DAILY_STEPS
    supervisor_run_id = new_supervisor_run_id()
    run_id = new_run_id()
    started_at = utc_now()
    _insert_run(supervisor_run_id, run_id, mode, strict_health_gate, started_at)

    latest_health_snapshot_id = None
    latest_health_status = None
    latest_cycle_id = None
    results: list[dict[str, Any]] = []
    run_status = 'complete'

    for step_order, step in enumerate(steps, start=1):
        if strict_health_gate and step.requires_healthy and latest_health_status not in {None, 'healthy'}:
            skipped_started_at = utc_now()
            skipped_finished_at = utc_now()
            skipped_summary = {
                'ok': False,
                'reason': 'strict_health_gate',
                'latest_health_status': latest_health_status,
            }
            _insert_step(
                supervisor_run_id,
                step_name=step.name,
                step_order=step_order,
                script_path=step.script_path,
                status='skipped',
                raw_output='',
                summary=skipped_summary,
                started_at=skipped_started_at,
                finished_at=skipped_finished_at,
            )
            results.append(
                {
                    'step_name': step.name,
                    'status': 'skipped',
                    'summary': skipped_summary,
                }
            )
            run_status = 'blocked'
            continue

        step_result = _run_step(step)
        raw_output = '\n'.join(part for part in [step_result['stdout'], step_result['stderr']] if part)
        _insert_step(
            supervisor_run_id,
            step_name=step_result['step_name'],
            step_order=step_order,
            script_path=step_result['script_path'],
            status=step_result['status'],
            raw_output=raw_output,
            summary={
                'returncode': step_result['returncode'],
                'stdout_summary': step_result['summary'],
                'stderr': step_result['stderr'],
            },
            started_at=step_result['started_at'],
            finished_at=step_result['finished_at'],
        )

        with connect() as conn:
            latest_health_snapshot_id, latest_health_status = _latest_health(conn)
            latest_cycle_id = _latest_cycle(conn)

        results.append(
            {
                'step_name': step_result['step_name'],
                'status': step_result['status'],
                'summary': step_result['summary'],
                'returncode': step_result['returncode'],
            }
        )

        if step_result['status'] != 'complete':
            run_status = 'failed'
            break

    finished_at = utc_now()
    summary = {
        'ok': run_status == 'complete',
        'supervisor_run_id': supervisor_run_id,
        'run_id': run_id,
        'mode': mode,
        'strict_health_gate': strict_health_gate,
        'status': run_status,
        'latest_health_snapshot_id': latest_health_snapshot_id,
        'latest_health_status': latest_health_status,
        'latest_cycle_id': latest_cycle_id,
        'steps': results,
        'step_count': len(results),
        'completed_steps': sum(1 for item in results if item['status'] == 'complete'),
        'skipped_steps': sum(1 for item in results if item['status'] == 'skipped'),
        'failed_steps': sum(1 for item in results if item['status'] == 'failed'),
        'started_at': started_at.isoformat() if started_at else None,
        'finished_at': finished_at.isoformat() if finished_at else None,
    }
    summary = _json_safe(summary)
    _update_run(
        supervisor_run_id,
        status=run_status,
        latest_health_snapshot_id=latest_health_snapshot_id,
        latest_health_status=latest_health_status,
        latest_cycle_id=latest_cycle_id,
        summary=summary,
        finished_at=finished_at,
    )
    write_worker_run(
        run_id=run_id,
        job_name=f'supervisor_run_{mode}_cycle',
        dataset_name='supervisor_orchestration',
        status='complete' if run_status == 'complete' else ('failed' if run_status == 'failed' else 'complete'),
        started_at=started_at,
        finished_at=finished_at,
        rows_written=len(results),
        rows_upserted=len(results),
        errors_count=1 if run_status == 'failed' else 0,
        summary_json=summary,
    )
    if run_status == 'failed':
        write_failure(
            failure_id=new_failure_id(),
            run_id=run_id,
            job_name=f'supervisor_run_{mode}_cycle',
            stage='orchestration',
            error_class='PipelineStepFailed',
            error_message='supervisor orchestration failed',
            retryable=False,
        )
    print(_json_dumps(summary))
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run the VietMarket supervisor cycle.')
    parser.add_argument('--mode', default='daily', choices=['daily'])
    parser.add_argument('--strict-health-gate', action='store_true')
    args = parser.parse_args()
    result = run_supervisor_cycle(mode=args.mode, strict_health_gate=args.strict_health_gate)
    raise SystemExit(0 if result['status'] in {'complete', 'blocked'} else 1)
