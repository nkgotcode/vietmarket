BEGIN;

CREATE TABLE IF NOT EXISTS theses (
  thesis_id TEXT PRIMARY KEY,
  cycle_id TEXT NOT NULL REFERENCES market_state_cycles(cycle_id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  thesis_type TEXT NOT NULL,
  side TEXT NOT NULL,
  horizon TEXT NOT NULL,
  confidence DOUBLE PRECISION NOT NULL,
  why_now TEXT NOT NULL,
  supporting_evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
  contradicting_evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
  invalidation JSONB NOT NULL DEFAULT '{}'::jsonb,
  suggested_priority INTEGER NOT NULL DEFAULT 0,
  notes TEXT NULL,
  raw_output_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  normalized_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (cycle_id, ticker)
);

CREATE TABLE IF NOT EXISTS recommendations (
  recommendation_id TEXT PRIMARY KEY,
  cycle_id TEXT NOT NULL REFERENCES market_state_cycles(cycle_id) ON DELETE CASCADE,
  thesis_id TEXT NOT NULL REFERENCES theses(thesis_id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft',
  side TEXT NOT NULL,
  horizon TEXT NOT NULL,
  confidence DOUBLE PRECISION NOT NULL,
  suggested_priority INTEGER NOT NULL DEFAULT 0,
  summary TEXT NOT NULL,
  why_now TEXT NOT NULL,
  supporting_evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
  contradicting_evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
  invalidation JSONB NOT NULL DEFAULT '{}'::jsonb,
  recommendation_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (cycle_id, ticker)
);

CREATE TABLE IF NOT EXISTS supervisor_decisions (
  decision_id TEXT PRIMARY KEY,
  cycle_id TEXT NOT NULL REFERENCES market_state_cycles(cycle_id) ON DELETE CASCADE,
  ticker TEXT NULL,
  decision_type TEXT NOT NULL,
  input_packet_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  raw_model_output_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  parsed_output_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  status TEXT NOT NULL DEFAULT 'complete',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS daily_briefs (
  brief_id TEXT PRIMARY KEY,
  cycle_id TEXT NOT NULL REFERENCES market_state_cycles(cycle_id) ON DELETE CASCADE,
  brief_type TEXT NOT NULL,
  title TEXT NOT NULL,
  summary_text TEXT NOT NULL,
  brief_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (cycle_id, brief_type)
);

CREATE TABLE IF NOT EXISTS recommendation_outcomes (
  outcome_id TEXT PRIMARY KEY,
  recommendation_id TEXT NOT NULL REFERENCES recommendations(recommendation_id) ON DELETE CASCADE,
  outcome_status TEXT NOT NULL,
  outcome_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_theses_cycle_priority
  ON theses(cycle_id, suggested_priority DESC, confidence DESC, ticker ASC);
CREATE INDEX IF NOT EXISTS idx_recommendations_cycle_status
  ON recommendations(cycle_id, status, suggested_priority DESC, confidence DESC, ticker ASC);
CREATE INDEX IF NOT EXISTS idx_supervisor_decisions_cycle_type
  ON supervisor_decisions(cycle_id, decision_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_daily_briefs_cycle_type
  ON daily_briefs(cycle_id, brief_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_recommendation_outcomes_recommendation
  ON recommendation_outcomes(recommendation_id, created_at DESC);

COMMIT;
