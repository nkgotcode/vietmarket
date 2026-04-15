BEGIN;

CREATE TABLE IF NOT EXISTS ticker_forward_outcomes (
  outcome_id TEXT PRIMARY KEY,
  recommendation_id TEXT NULL REFERENCES recommendations(recommendation_id) ON DELETE CASCADE,
  cycle_id TEXT NOT NULL REFERENCES market_state_cycles(cycle_id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  horizon_days INTEGER NOT NULL,
  entry_ts BIGINT NULL,
  exit_ts BIGINT NULL,
  benchmark_ticker TEXT NULL,
  entry_price DOUBLE PRECISION NULL,
  exit_price DOUBLE PRECISION NULL,
  benchmark_entry_price DOUBLE PRECISION NULL,
  benchmark_exit_price DOUBLE PRECISION NULL,
  forward_return DOUBLE PRECISION NULL,
  benchmark_return DOUBLE PRECISION NULL,
  excess_return DOUBLE PRECISION NULL,
  max_drawdown DOUBLE PRECISION NULL,
  max_favorable_excursion DOUBLE PRECISION NULL,
  liquidity_bucket TEXT NULL,
  sector TEXT NULL,
  market_regime TEXT NULL,
  label_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (cycle_id, ticker, horizon_days)
);

CREATE TABLE IF NOT EXISTS calibration_runs (
  calibration_run_id TEXT PRIMARY KEY,
  score_version TEXT NOT NULL,
  scope TEXT NOT NULL,
  summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS calibration_buckets (
  calibration_run_id TEXT NOT NULL REFERENCES calibration_runs(calibration_run_id) ON DELETE CASCADE,
  bucket_name TEXT NOT NULL,
  horizon_days INTEGER NOT NULL,
  sample_size INTEGER NOT NULL DEFAULT 0,
  avg_forward_return DOUBLE PRECISION NULL,
  median_forward_return DOUBLE PRECISION NULL,
  positive_rate DOUBLE PRECISION NULL,
  avg_excess_return DOUBLE PRECISION NULL,
  avg_max_drawdown DOUBLE PRECISION NULL,
  metric_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (calibration_run_id, bucket_name, horizon_days)
);

CREATE TABLE IF NOT EXISTS cohort_metrics (
  cohort_metric_id TEXT PRIMARY KEY,
  cohort_type TEXT NOT NULL,
  cohort_key TEXT NOT NULL,
  horizon_days INTEGER NOT NULL,
  sample_size INTEGER NOT NULL DEFAULT 0,
  positive_rate DOUBLE PRECISION NULL,
  avg_forward_return DOUBLE PRECISION NULL,
  median_forward_return DOUBLE PRECISION NULL,
  avg_excess_return DOUBLE PRECISION NULL,
  avg_max_drawdown DOUBLE PRECISION NULL,
  summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ticker_forward_outcomes_cycle_horizon
  ON ticker_forward_outcomes(cycle_id, horizon_days, ticker);
CREATE INDEX IF NOT EXISTS idx_ticker_forward_outcomes_recommendation
  ON ticker_forward_outcomes(recommendation_id, horizon_days, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ticker_forward_outcomes_regime
  ON ticker_forward_outcomes(market_regime, horizon_days, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_calibration_runs_created
  ON calibration_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_cohort_metrics_lookup
  ON cohort_metrics(cohort_type, cohort_key, horizon_days, created_at DESC);

COMMIT;
