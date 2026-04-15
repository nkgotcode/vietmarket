BEGIN;

CREATE TABLE IF NOT EXISTS score_versions (
  score_version TEXT PRIMARY KEY,
  status TEXT NOT NULL DEFAULT 'active',
  description TEXT NOT NULL,
  config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS alpha_scores (
  cycle_id TEXT NOT NULL REFERENCES market_state_cycles(cycle_id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  score_version TEXT NOT NULL REFERENCES score_versions(score_version) ON DELETE CASCADE,
  alpha_score DOUBLE PRECISION NOT NULL DEFAULT 0,
  model_confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
  reason_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (cycle_id, ticker, score_version)
);

CREATE TABLE IF NOT EXISTS quality_scores (
  cycle_id TEXT NOT NULL REFERENCES market_state_cycles(cycle_id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  score_version TEXT NOT NULL REFERENCES score_versions(score_version) ON DELETE CASCADE,
  quality_score DOUBLE PRECISION NOT NULL DEFAULT 0,
  evidence_confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
  reason_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (cycle_id, ticker, score_version)
);

CREATE TABLE IF NOT EXISTS risk_scores_v2 (
  cycle_id TEXT NOT NULL REFERENCES market_state_cycles(cycle_id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  score_version TEXT NOT NULL REFERENCES score_versions(score_version) ON DELETE CASCADE,
  risk_score DOUBLE PRECISION NOT NULL DEFAULT 0,
  block_flag BOOLEAN NOT NULL DEFAULT FALSE,
  reason_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (cycle_id, ticker, score_version)
);

CREATE TABLE IF NOT EXISTS execution_scores (
  cycle_id TEXT NOT NULL REFERENCES market_state_cycles(cycle_id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  score_version TEXT NOT NULL REFERENCES score_versions(score_version) ON DELETE CASCADE,
  execution_score DOUBLE PRECISION NOT NULL DEFAULT 0,
  execution_confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
  reason_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (cycle_id, ticker, score_version)
);

CREATE TABLE IF NOT EXISTS decision_scores (
  cycle_id TEXT NOT NULL REFERENCES market_state_cycles(cycle_id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  score_version TEXT NOT NULL REFERENCES score_versions(score_version) ON DELETE CASCADE,
  alpha_score DOUBLE PRECISION NOT NULL DEFAULT 0,
  quality_score DOUBLE PRECISION NOT NULL DEFAULT 0,
  risk_score DOUBLE PRECISION NOT NULL DEFAULT 0,
  execution_score DOUBLE PRECISION NOT NULL DEFAULT 0,
  decision_score DOUBLE PRECISION NOT NULL DEFAULT 0,
  model_confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
  evidence_confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
  execution_confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
  recommended_state TEXT NOT NULL DEFAULT 'research_only',
  paper_eligible BOOLEAN NOT NULL DEFAULT FALSE,
  block_reason_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  score_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (cycle_id, ticker, score_version)
);

CREATE INDEX IF NOT EXISTS idx_decision_scores_cycle_version_score
  ON decision_scores(cycle_id, score_version, paper_eligible, decision_score DESC, ticker ASC);
CREATE INDEX IF NOT EXISTS idx_decision_scores_state
  ON decision_scores(score_version, recommended_state, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alpha_scores_cycle
  ON alpha_scores(cycle_id, score_version, alpha_score DESC, ticker ASC);
CREATE INDEX IF NOT EXISTS idx_execution_scores_cycle
  ON execution_scores(cycle_id, score_version, execution_score DESC, ticker ASC);

COMMIT;
