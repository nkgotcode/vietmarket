from __future__ import annotations

import uuid


def new_run_id() -> str:
    return f'run_{uuid.uuid4().hex}'


def new_snapshot_id() -> str:
    return f'snap_{uuid.uuid4().hex}'


def new_issue_id() -> str:
    return f'issue_{uuid.uuid4().hex}'


def new_failure_id() -> str:
    return f'fail_{uuid.uuid4().hex}'


def new_cycle_id() -> str:
    return f'cycle_{uuid.uuid4().hex}'


def new_thesis_id() -> str:
    return f'thesis_{uuid.uuid4().hex}'


def new_recommendation_id() -> str:
    return f'reco_{uuid.uuid4().hex}'


def new_decision_id() -> str:
    return f'decision_{uuid.uuid4().hex}'


def new_brief_id() -> str:
    return f'brief_{uuid.uuid4().hex}'


def new_outcome_id() -> str:
    return f'outcome_{uuid.uuid4().hex}'



def new_supervisor_run_id() -> str:
    return f'srun_{uuid.uuid4().hex}'



def new_supervisor_step_id() -> str:
    return f'sstep_{uuid.uuid4().hex}'