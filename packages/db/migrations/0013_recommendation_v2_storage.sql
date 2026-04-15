BEGIN;

CREATE TABLE IF NOT EXISTS recommendation_scorecards (
  recommendation_id TEXT PRIMARY KEY REFERENCES recommendations(recommendation_id) ON DELETE CASCADE,
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
  scorecard_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS promotion_decisions (
  promotion_decision_id TEXT PRIMARY KEY,
  recommendation_id TEXT NOT NULL REFERENCES recommendations(recommendation_id) ON DELETE CASCADE,
  cycle_id TEXT NOT NULL REFERENCES market_state_cycles(cycle_id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  score_version TEXT NOT NULL REFERENCES score_versions(score_version) ON DELETE CASCADE,
  promotion_state TEXT NOT NULL,
  paper_eligible BOOLEAN NOT NULL DEFAULT FALSE,
  decision_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (cycle_id, ticker, score_version)
);

CREATE INDEX IF NOT EXISTS idx_recommendation_scorecards_cycle
  ON recommendation_scorecards(cycle_id, score_version, decision_score DESC, ticker ASC);
CREATE INDEX IF NOT EXISTS idx_promotion_decisions_cycle
  ON promotion_decisions(cycle_id, score_version, paper_eligible, promotion_state, created_at DESC);

COMMIT;
