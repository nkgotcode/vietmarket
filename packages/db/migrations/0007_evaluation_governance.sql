BEGIN;

CREATE TABLE IF NOT EXISTS replay_runs (
  replay_run_id TEXT PRIMARY KEY,
  cycle_id TEXT NOT NULL REFERENCES market_state_cycles(cycle_id) ON DELETE CASCADE,
  replay_scope TEXT NOT NULL,
  summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS replay_results (
  replay_run_id TEXT NOT NULL REFERENCES replay_runs(replay_run_id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  result_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (replay_run_id, ticker)
);

CREATE TABLE IF NOT EXISTS prompt_versions (
  prompt_name TEXT PRIMARY KEY,
  prompt_version TEXT NOT NULL,
  prompt_text TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS model_runs (
  model_run_id TEXT PRIMARY KEY,
  cycle_id TEXT NULL REFERENCES market_state_cycles(cycle_id) ON DELETE SET NULL,
  run_kind TEXT NOT NULL,
  model_name TEXT NOT NULL,
  summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS recommendation_outcomes (
  outcome_id TEXT PRIMARY KEY,
  recommendation_id TEXT NOT NULL REFERENCES recommendations(recommendation_id) ON DELETE CASCADE,
  outcome_status TEXT NOT NULL,
  outcome_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS calibration_metrics (
  metric_name TEXT PRIMARY KEY,
  metric_value DOUBLE PRECISION NOT NULL,
  metric_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_replay_runs_cycle_created ON replay_runs(cycle_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_model_runs_cycle_kind ON model_runs(cycle_id, run_kind, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_recommendation_outcomes_created ON recommendation_outcomes(created_at DESC);

COMMIT;
