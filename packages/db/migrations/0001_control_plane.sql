BEGIN;

CREATE TABLE IF NOT EXISTS schema_migrations (
  name TEXT PRIMARY KEY,
  applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS worker_runs (
  run_id TEXT PRIMARY KEY,
  job_name TEXT NOT NULL,
  dataset_name TEXT NULL,
  nomad_job_id TEXT NULL,
  nomad_alloc_id TEXT NULL,
  node_name TEXT NULL,
  started_at TIMESTAMPTZ NOT NULL,
  finished_at TIMESTAMPTZ NULL,
  status TEXT NOT NULL,
  rows_read INTEGER NOT NULL DEFAULT 0,
  rows_written INTEGER NOT NULL DEFAULT 0,
  rows_upserted INTEGER NOT NULL DEFAULT 0,
  warnings_count INTEGER NOT NULL DEFAULT 0,
  errors_count INTEGER NOT NULL DEFAULT 0,
  summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS worker_failures (
  failure_id TEXT PRIMARY KEY,
  run_id TEXT NULL REFERENCES worker_runs(run_id) ON DELETE SET NULL,
  job_name TEXT NOT NULL,
  stage TEXT NULL,
  error_class TEXT NOT NULL,
  error_hash TEXT NOT NULL,
  error_message TEXT NOT NULL,
  retryable BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS dataset_freshness (
  freshness_id TEXT PRIMARY KEY,
  dataset_name TEXT NOT NULL,
  ticker TEXT NOT NULL DEFAULT '',
  tf TEXT NOT NULL DEFAULT '',
  max_event_ts TIMESTAMPTZ NULL,
  max_ingested_at TIMESTAMPTZ NULL,
  freshness_seconds BIGINT NULL,
  freshness_status TEXT NOT NULL,
  freshness_context_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (dataset_name, ticker, tf)
);

CREATE TABLE IF NOT EXISTS system_health_snapshots (
  snapshot_id TEXT PRIMARY KEY,
  cycle_id TEXT NULL,
  overall_status TEXT NOT NULL,
  data_plane_status TEXT NOT NULL,
  freshness_status TEXT NOT NULL,
  notes_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS system_health_issues (
  issue_id TEXT PRIMARY KEY,
  snapshot_id TEXT NOT NULL REFERENCES system_health_snapshots(snapshot_id) ON DELETE CASCADE,
  severity TEXT NOT NULL,
  scope_type TEXT NOT NULL,
  scope_key TEXT NOT NULL,
  issue_code TEXT NOT NULL,
  issue_message TEXT NOT NULL,
  blocking BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_worker_runs_job_started ON worker_runs(job_name, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_worker_failures_job_created ON worker_failures(job_name, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_dataset_freshness_lookup ON dataset_freshness(dataset_name, ticker, tf);
CREATE INDEX IF NOT EXISTS idx_system_health_snapshots_created ON system_health_snapshots(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_system_health_issues_snapshot ON system_health_issues(snapshot_id, severity, blocking);

COMMIT;