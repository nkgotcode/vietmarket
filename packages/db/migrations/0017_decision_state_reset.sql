BEGIN;

CREATE TABLE IF NOT EXISTS decision_states_v2 (
  cycle_id TEXT NOT NULL REFERENCES market_state_cycles(cycle_id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  grade_version TEXT NOT NULL REFERENCES grade_versions(grade_version) ON DELETE CASCADE,
  analytical_state TEXT NOT NULL,
  final_state TEXT NOT NULL,
  paper_eligible BOOLEAN NOT NULL DEFAULT FALSE,
  policy_blocked BOOLEAN NOT NULL DEFAULT FALSE,
  policy_reason TEXT NULL,
  state_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (cycle_id, ticker, grade_version)
);

CREATE INDEX IF NOT EXISTS idx_decision_states_v2_cycle
  ON decision_states_v2(cycle_id, grade_version, paper_eligible, final_state, ticker ASC);

COMMIT;
