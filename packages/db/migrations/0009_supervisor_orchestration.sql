BEGIN;

CREATE TABLE IF NOT EXISTS supervisor_runs (
  supervisor_run_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL UNIQUE,
  run_type TEXT NOT NULL,
  mode TEXT NOT NULL,
  requested_by TEXT NULL,
  strict_health_gate BOOLEAN NOT NULL DEFAULT false,
  nomad_job_id TEXT NULL,
  nomad_alloc_id TEXT NULL,
  latest_health_snapshot_id TEXT NULL,
  latest_health_status TEXT NULL,
  latest_cycle_id TEXT NULL REFERENCES market_state_cycles(cycle_id) ON DELETE SET NULL,
  status TEXT NOT NULL,
  summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  started_at TIMESTAMPTZ NOT NULL,
  finished_at TIMESTAMPTZ NULL
);

CREATE TABLE IF NOT EXISTS supervisor_run_steps (
  supervisor_step_id TEXT PRIMARY KEY,
  supervisor_run_id TEXT NOT NULL REFERENCES supervisor_runs(supervisor_run_id) ON DELETE CASCADE,
  step_name TEXT NOT NULL,
  step_order INTEGER NOT NULL,
  script_path TEXT NOT NULL,
  status TEXT NOT NULL,
  raw_output TEXT NULL,
  summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  started_at TIMESTAMPTZ NOT NULL,
  finished_at TIMESTAMPTZ NULL,
  UNIQUE (supervisor_run_id, step_order),
  UNIQUE (supervisor_run_id, step_name)
);

CREATE INDEX IF NOT EXISTS idx_supervisor_runs_status_started
  ON supervisor_runs(status, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_supervisor_runs_mode_started
  ON supervisor_runs(mode, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_supervisor_runs_cycle_started
  ON supervisor_runs(latest_cycle_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_supervisor_run_steps_run_order
  ON supervisor_run_steps(supervisor_run_id, step_order ASC);
CREATE INDEX IF NOT EXISTS idx_supervisor_run_steps_status_started
  ON supervisor_run_steps(status, started_at DESC);

COMMIT;
