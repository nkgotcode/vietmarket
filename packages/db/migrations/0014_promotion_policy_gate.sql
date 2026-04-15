BEGIN;

CREATE TABLE IF NOT EXISTS promotion_policy_versions (
  promotion_policy_version TEXT PRIMARY KEY,
  status TEXT NOT NULL DEFAULT 'active',
  paper_trading_enabled BOOLEAN NOT NULL DEFAULT FALSE,
  thresholds_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  notes_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS paper_trade_admissions (
  admission_id TEXT PRIMARY KEY,
  recommendation_id TEXT NOT NULL REFERENCES recommendations(recommendation_id) ON DELETE CASCADE,
  cycle_id TEXT NOT NULL REFERENCES market_state_cycles(cycle_id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  score_version TEXT NOT NULL REFERENCES score_versions(score_version) ON DELETE CASCADE,
  promotion_policy_version TEXT NOT NULL REFERENCES promotion_policy_versions(promotion_policy_version) ON DELETE CASCADE,
  admission_status TEXT NOT NULL,
  policy_result TEXT NULL,
  paper_trading_enabled BOOLEAN NOT NULL DEFAULT FALSE,
  admission_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (cycle_id, ticker, score_version, promotion_policy_version)
);

CREATE INDEX IF NOT EXISTS idx_promotion_policy_versions_created
  ON promotion_policy_versions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_paper_trade_admissions_cycle
  ON paper_trade_admissions(cycle_id, admission_status, created_at DESC);

COMMIT;
