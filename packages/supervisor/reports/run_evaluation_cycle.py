#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from packages.supervisor.common.ids import new_failure_id, new_run_id
from packages.supervisor.common.time import utc_now
from packages.supervisor.health.failure_writer import write_failure
from packages.supervisor.health.worker_run_writer import write_worker_run

SCRIPTS = (
    ('build_forward_labels', 'packages/supervisor/evaluation/build_forward_labels.py'),
    ('evaluate_recommendations', 'packages/supervisor/reports/evaluate_recommendations.py'),
    ('run_replay', 'packages/supervisor/reports/run_replay.py'),
    ('analyze_score_deciles', 'packages/supervisor/evaluation/analyze_score_deciles.py'),
    ('analyze_regime_stability', 'packages/supervisor/evaluation/analyze_regime_stability.py'),
    ('calibration', 'packages/supervisor/reports/calibration.py'),
    ('build_feature_snapshots', 'packages/supervisor/grading/build_feature_snapshots.py'),
    ('build_estimates', 'packages/supervisor/grading/build_estimates.py'),
    ('calibrate_grades', 'packages/supervisor/grading/calibrate_grades.py'),
    ('build_grades', 'packages/supervisor/grading/build_grades.py'),
    ('build_decision_states', 'packages/supervisor/grading/build_decision_states.py'),
    ('build_scores_v2', 'packages/supervisor/scoring/build_scores_v2.py'),
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


def run_evaluation_cycle() -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for step_name, rel_path in SCRIPTS:
        proc = subprocess.run(
            [sys.executable, str(repo_root() / rel_path)],
            cwd=repo_root(),
            env=os.environ.copy(),
            capture_output=True,
            text=True,
        )
        payload = _extract_json(proc.stdout.strip()) or {}
        status = 'complete' if proc.returncode == 0 else 'failed'
        result = {
            'step_name': step_name,
            'script_path': rel_path,
            'status': status,
            'returncode': proc.returncode,
            'summary': payload,
            'stderr': proc.stderr.strip(),
        }
        results.append(result)
        if status != 'complete':
            raise RuntimeError(_json_dumps(_json_safe({'failed_step': step_name, 'results': results})))
    return _json_safe({'ok': True, 'step_count': len(results), 'steps': results})


if __name__ == '__main__':
    run_id = new_run_id()
    started_at = utc_now()
    try:
        result = run_evaluation_cycle()
        finished_at = utc_now()
        write_worker_run(
            run_id=run_id,
            job_name='supervisor_run_evaluation_cycle',
            dataset_name='evaluation_governance',
            status='complete',
            started_at=started_at,
            finished_at=finished_at,
            rows_written=result['step_count'],
            rows_upserted=result['step_count'],
            summary_json=result,
        )
        print(_json_dumps(result))
    except Exception as exc:
        finished_at = utc_now()
        write_worker_run(
            run_id=run_id,
            job_name='supervisor_run_evaluation_cycle',
            dataset_name='evaluation_governance',
            status='failed',
            started_at=started_at,
            finished_at=finished_at,
            errors_count=1,
            summary_json={'error': str(exc)},
        )
        write_failure(
            failure_id=new_failure_id(),
            run_id=run_id,
            job_name='supervisor_run_evaluation_cycle',
            stage='evaluation_cycle',
            error_class=type(exc).__name__,
            error_message=str(exc),
            retryable=False,
        )
        raise
