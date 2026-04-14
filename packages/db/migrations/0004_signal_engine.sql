BEGIN;

CREATE TABLE IF NOT EXISTS signal_scores (
  cycle_id TEXT NOT NULL REFERENCES market_state_cycles(cycle_id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  signal_family TEXT NOT NULL,
  score_raw DOUBLE PRECISION NOT NULL DEFAULT 0,
  score_normalized DOUBLE PRECISION NOT NULL DEFAULT 0,
  confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
  horizon TEXT NOT NULL DEFAULT 'swing',
  expires_at TIMESTAMPTZ NULL,
  blocking_flag BOOLEAN NOT NULL DEFAULT FALSE,
  reason_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (cycle_id, ticker, signal_family)
);

CREATE TABLE IF NOT EXISTS signal_components (
  cycle_id TEXT NOT NULL REFERENCES market_state_cycles(cycle_id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  signal_family TEXT NOT NULL,
  component_name TEXT NOT NULL,
  component_value DOUBLE PRECISION NULL,
  component_weight DOUBLE PRECISION NULL,
  component_note TEXT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (cycle_id, ticker, signal_family, component_name)
);

CREATE TABLE IF NOT EXISTS signal_policies (
  policy_name TEXT PRIMARY KEY,
  policy_version TEXT NOT NULL,
  policy_scope TEXT NOT NULL DEFAULT 'phase3_signal_engine',
  weights_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  blocking_rules_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  notes_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS candidate_rankings (
  cycle_id TEXT NOT NULL REFERENCES market_state_cycles(cycle_id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  total_score DOUBLE PRECISION NOT NULL DEFAULT 0,
  total_confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
  ranking_bucket TEXT NOT NULL DEFAULT 'watch',
  blocking_flag BOOLEAN NOT NULL DEFAULT FALSE,
  ranking_reason_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (cycle_id, ticker)
);

CREATE INDEX IF NOT EXISTS idx_signal_scores_cycle_family_score
  ON signal_scores(cycle_id, signal_family, score_normalized DESC, ticker ASC);
CREATE INDEX IF NOT EXISTS idx_signal_scores_ticker_created
  ON signal_scores(ticker, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_signal_components_cycle_ticker
  ON signal_components(cycle_id, ticker, signal_family);
CREATE INDEX IF NOT EXISTS idx_candidate_rankings_cycle_score
  ON candidate_rankings(cycle_id, blocking_flag, total_score DESC, ticker ASC);
CREATE INDEX IF NOT EXISTS idx_candidate_rankings_ticker_created
  ON candidate_rankings(ticker, created_at DESC);

COMMIT;
