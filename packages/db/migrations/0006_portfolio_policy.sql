BEGIN;

CREATE TABLE IF NOT EXISTS risk_limits (
  limit_name TEXT PRIMARY KEY,
  limit_scope TEXT NOT NULL DEFAULT 'global',
  limit_value DOUBLE PRECISION NOT NULL,
  notes_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS policy_results (
  cycle_id TEXT NOT NULL REFERENCES market_state_cycles(cycle_id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  recommendation_id TEXT NULL REFERENCES recommendations(recommendation_id) ON DELETE SET NULL,
  overall_result TEXT NOT NULL,
  blocking_flag BOOLEAN NOT NULL DEFAULT FALSE,
  checks_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (cycle_id, ticker)
);

CREATE TABLE IF NOT EXISTS execution_intents (
  intent_id TEXT PRIMARY KEY,
  cycle_id TEXT NOT NULL REFERENCES market_state_cycles(cycle_id) ON DELETE CASCADE,
  recommendation_id TEXT NULL REFERENCES recommendations(recommendation_id) ON DELETE SET NULL,
  ticker TEXT NOT NULL,
  intent_status TEXT NOT NULL DEFAULT 'pending',
  side TEXT NOT NULL,
  target_qty DOUBLE PRECISION NOT NULL DEFAULT 0,
  reference_price DOUBLE PRECISION NULL,
  notes_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS paper_orders (
  paper_order_id TEXT PRIMARY KEY,
  intent_id TEXT NOT NULL REFERENCES execution_intents(intent_id) ON DELETE CASCADE,
  cycle_id TEXT NOT NULL REFERENCES market_state_cycles(cycle_id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  order_status TEXT NOT NULL DEFAULT 'created',
  side TEXT NOT NULL,
  qty DOUBLE PRECISION NOT NULL,
  limit_price DOUBLE PRECISION NULL,
  submitted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS paper_fills (
  paper_fill_id TEXT PRIMARY KEY,
  paper_order_id TEXT NOT NULL REFERENCES paper_orders(paper_order_id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  fill_qty DOUBLE PRECISION NOT NULL,
  fill_price DOUBLE PRECISION NOT NULL,
  filled_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  notes_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS positions (
  ticker TEXT PRIMARY KEY,
  qty DOUBLE PRECISION NOT NULL DEFAULT 0,
  avg_cost DOUBLE PRECISION NOT NULL DEFAULT 0,
  market_price DOUBLE PRECISION NULL,
  market_value DOUBLE PRECISION NULL,
  unrealized_pnl DOUBLE PRECISION NOT NULL DEFAULT 0,
  realized_pnl DOUBLE PRECISION NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS position_events (
  event_id TEXT PRIMARY KEY,
  ticker TEXT NOT NULL,
  event_type TEXT NOT NULL,
  qty_delta DOUBLE PRECISION NOT NULL DEFAULT 0,
  price DOUBLE PRECISION NULL,
  related_order_id TEXT NULL,
  notes_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
  snapshot_id TEXT PRIMARY KEY,
  cycle_id TEXT NOT NULL REFERENCES market_state_cycles(cycle_id) ON DELETE CASCADE,
  cash_balance DOUBLE PRECISION NOT NULL DEFAULT 1000000000,
  gross_exposure DOUBLE PRECISION NOT NULL DEFAULT 0,
  net_exposure DOUBLE PRECISION NOT NULL DEFAULT 0,
  market_value DOUBLE PRECISION NOT NULL DEFAULT 0,
  unrealized_pnl DOUBLE PRECISION NOT NULL DEFAULT 0,
  realized_pnl DOUBLE PRECISION NOT NULL DEFAULT 0,
  positions_count INTEGER NOT NULL DEFAULT 0,
  snapshot_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_policy_results_cycle_result ON policy_results(cycle_id, blocking_flag, overall_result, ticker);
CREATE INDEX IF NOT EXISTS idx_execution_intents_cycle_status ON execution_intents(cycle_id, intent_status, ticker);
CREATE INDEX IF NOT EXISTS idx_paper_orders_cycle_status ON paper_orders(cycle_id, order_status, ticker);
CREATE INDEX IF NOT EXISTS idx_paper_fills_order ON paper_fills(paper_order_id, filled_at DESC);
CREATE INDEX IF NOT EXISTS idx_position_events_ticker_created ON position_events(ticker, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_portfolio_snapshots_cycle_created ON portfolio_snapshots(cycle_id, created_at DESC);

COMMIT;
