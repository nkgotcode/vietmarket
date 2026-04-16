BEGIN;

CREATE TABLE IF NOT EXISTS feature_snapshots (
  cycle_id TEXT NOT NULL REFERENCES market_state_cycles(cycle_id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  grade_version TEXT NOT NULL REFERENCES grade_versions(grade_version) ON DELETE CASCADE,
  market_regime TEXT NULL,
  regime_confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
  feature_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  feature_quality_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (cycle_id, ticker, grade_version)
);

CREATE INDEX IF NOT EXISTS idx_feature_snapshots_cycle_version
  ON feature_snapshots(cycle_id, grade_version, ticker ASC);
CREATE INDEX IF NOT EXISTS idx_feature_snapshots_regime
  ON feature_snapshots(grade_version, market_regime, created_at DESC);

COMMIT;
