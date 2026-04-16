BEGIN;

CREATE TABLE IF NOT EXISTS grade_versions (
  grade_version TEXT PRIMARY KEY,
  status TEXT NOT NULL DEFAULT 'active',
  description TEXT NOT NULL,
  semantics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS estimate_snapshots (
  cycle_id TEXT NOT NULL REFERENCES market_state_cycles(cycle_id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  grade_version TEXT NOT NULL REFERENCES grade_versions(grade_version) ON DELETE CASCADE,
  edge_estimate DOUBLE PRECISION NOT NULL DEFAULT 0,
  downside_estimate DOUBLE PRECISION NOT NULL DEFAULT 0,
  execution_cost_estimate DOUBLE PRECISION NOT NULL DEFAULT 0,
  data_reliability_estimate DOUBLE PRECISION NOT NULL DEFAULT 0,
  estimate_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (cycle_id, ticker, grade_version)
);

CREATE TABLE IF NOT EXISTS opportunity_grades (
  cycle_id TEXT NOT NULL REFERENCES market_state_cycles(cycle_id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  grade_version TEXT NOT NULL REFERENCES grade_versions(grade_version) ON DELETE CASCADE,
  grade_label TEXT NOT NULL DEFAULT 'F',
  grade_value DOUBLE PRECISION NOT NULL DEFAULT 0,
  grade_percentile DOUBLE PRECISION NOT NULL DEFAULT 0,
  reason_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (cycle_id, ticker, grade_version)
);

CREATE TABLE IF NOT EXISTS evidence_grades (
  cycle_id TEXT NOT NULL REFERENCES market_state_cycles(cycle_id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  grade_version TEXT NOT NULL REFERENCES grade_versions(grade_version) ON DELETE CASCADE,
  grade_label TEXT NOT NULL DEFAULT 'invalid',
  reliability_index DOUBLE PRECISION NOT NULL DEFAULT 0,
  reason_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (cycle_id, ticker, grade_version)
);

CREATE TABLE IF NOT EXISTS tradability_grades (
  cycle_id TEXT NOT NULL REFERENCES market_state_cycles(cycle_id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  grade_version TEXT NOT NULL REFERENCES grade_versions(grade_version) ON DELETE CASCADE,
  grade_label TEXT NOT NULL DEFAULT 'untradeable',
  tradability_index DOUBLE PRECISION NOT NULL DEFAULT 0,
  execution_cost_estimate DOUBLE PRECISION NOT NULL DEFAULT 0,
  capacity_band TEXT NOT NULL DEFAULT 'unknown',
  reason_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (cycle_id, ticker, grade_version)
);

CREATE TABLE IF NOT EXISTS risk_containment_grades (
  cycle_id TEXT NOT NULL REFERENCES market_state_cycles(cycle_id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  grade_version TEXT NOT NULL REFERENCES grade_versions(grade_version) ON DELETE CASCADE,
  grade_label TEXT NOT NULL DEFAULT 'hazardous',
  containment_index DOUBLE PRECISION NOT NULL DEFAULT 0,
  reason_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (cycle_id, ticker, grade_version)
);

CREATE TABLE IF NOT EXISTS reliability_snapshots (
  cycle_id TEXT NOT NULL REFERENCES market_state_cycles(cycle_id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  grade_version TEXT NOT NULL REFERENCES grade_versions(grade_version) ON DELETE CASCADE,
  forecast_reliability DOUBLE PRECISION NOT NULL DEFAULT 0,
  evidence_reliability DOUBLE PRECISION NOT NULL DEFAULT 0,
  execution_reliability DOUBLE PRECISION NOT NULL DEFAULT 0,
  reliability_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (cycle_id, ticker, grade_version)
);

CREATE INDEX IF NOT EXISTS idx_estimate_snapshots_cycle_version
  ON estimate_snapshots(cycle_id, grade_version, ticker ASC);
CREATE INDEX IF NOT EXISTS idx_opportunity_grades_cycle
  ON opportunity_grades(cycle_id, grade_version, grade_value DESC, ticker ASC);
CREATE INDEX IF NOT EXISTS idx_evidence_grades_cycle
  ON evidence_grades(cycle_id, grade_version, reliability_index DESC, ticker ASC);
CREATE INDEX IF NOT EXISTS idx_tradability_grades_cycle
  ON tradability_grades(cycle_id, grade_version, tradability_index DESC, ticker ASC);
CREATE INDEX IF NOT EXISTS idx_risk_containment_grades_cycle
  ON risk_containment_grades(cycle_id, grade_version, containment_index DESC, ticker ASC);
CREATE INDEX IF NOT EXISTS idx_reliability_snapshots_cycle
  ON reliability_snapshots(cycle_id, grade_version, forecast_reliability DESC, ticker ASC);

COMMIT;
