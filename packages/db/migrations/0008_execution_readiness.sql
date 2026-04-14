BEGIN;

CREATE TABLE IF NOT EXISTS broker_accounts (
  account_id TEXT PRIMARY KEY,
  broker_name TEXT NOT NULL,
  account_label TEXT NOT NULL,
  account_status TEXT NOT NULL DEFAULT 'paper_only',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS broker_order_staging (
  staging_id TEXT PRIMARY KEY,
  recommendation_id TEXT NULL REFERENCES recommendations(recommendation_id) ON DELETE SET NULL,
  paper_order_id TEXT NULL REFERENCES paper_orders(paper_order_id) ON DELETE SET NULL,
  ticker TEXT NOT NULL,
  side TEXT NOT NULL,
  qty DOUBLE PRECISION NOT NULL,
  stage_status TEXT NOT NULL DEFAULT 'pending_approval',
  stage_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS broker_order_audit (
  audit_id TEXT PRIMARY KEY,
  staging_id TEXT NOT NULL REFERENCES broker_order_staging(staging_id) ON DELETE CASCADE,
  audit_event TEXT NOT NULL,
  audit_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS broker_positions_mirror (
  account_id TEXT NOT NULL,
  ticker TEXT NOT NULL,
  qty DOUBLE PRECISION NOT NULL DEFAULT 0,
  market_value DOUBLE PRECISION NULL,
  mirror_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (account_id, ticker)
);

CREATE TABLE IF NOT EXISTS execution_approvals (
  approval_id TEXT PRIMARY KEY,
  staging_id TEXT NOT NULL REFERENCES broker_order_staging(staging_id) ON DELETE CASCADE,
  approval_status TEXT NOT NULL DEFAULT 'required',
  approver TEXT NULL,
  approval_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_broker_order_staging_status ON broker_order_staging(stage_status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_broker_order_audit_staging ON broker_order_audit(staging_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_execution_approvals_status ON execution_approvals(approval_status, created_at DESC);

COMMIT;
