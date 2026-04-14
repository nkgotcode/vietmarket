BEGIN;

CREATE TABLE IF NOT EXISTS market_state_cycles (
  cycle_id TEXT PRIMARY KEY,
  source_health_snapshot_id TEXT NULL REFERENCES system_health_snapshots(snapshot_id) ON DELETE SET NULL,
  overall_status TEXT NOT NULL,
  freshness_status TEXT NOT NULL,
  frontier_status TEXT NOT NULL,
  universe_count INTEGER NOT NULL DEFAULT 0,
  regime_code TEXT NULL,
  notes_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ticker_snapshots (
  cycle_id TEXT NOT NULL REFERENCES market_state_cycles(cycle_id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  exchange TEXT NULL,
  sector TEXT NULL,
  price_last DOUBLE PRECISION NULL,
  volume_last DOUBLE PRECISION NULL,
  turnover_last DOUBLE PRECISION NULL,
  ret_1d DOUBLE PRECISION NULL,
  ret_5d DOUBLE PRECISION NULL,
  ret_20d DOUBLE PRECISION NULL,
  sma20_gap DOUBLE PRECISION NULL,
  sma50_gap DOUBLE PRECISION NULL,
  ema20_gap DOUBLE PRECISION NULL,
  volatility_20d DOUBLE PRECISION NULL,
  article_count_24h INTEGER NOT NULL DEFAULT 0,
  corporate_action_flag BOOLEAN NOT NULL DEFAULT FALSE,
  financial_recency_days INTEGER NULL,
  liquidity_bucket TEXT NOT NULL DEFAULT 'unknown',
  trend_state TEXT NOT NULL DEFAULT 'unknown',
  momentum_state TEXT NOT NULL DEFAULT 'unknown',
  watchlist_score DOUBLE PRECISION NOT NULL DEFAULT 0,
  health_status TEXT NOT NULL DEFAULT 'unknown',
  snapshot_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (cycle_id, ticker)
);

CREATE TABLE IF NOT EXISTS sector_snapshots (
  cycle_id TEXT NOT NULL REFERENCES market_state_cycles(cycle_id) ON DELETE CASCADE,
  sector TEXT NOT NULL,
  names_count INTEGER NOT NULL DEFAULT 0,
  adv_count INTEGER NOT NULL DEFAULT 0,
  dec_count INTEGER NOT NULL DEFAULT 0,
  breadth_pct DOUBLE PRECISION NULL,
  avg_ret_1d DOUBLE PRECISION NULL,
  avg_ret_5d DOUBLE PRECISION NULL,
  leadership_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  laggards_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  snapshot_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (cycle_id, sector)
);

CREATE TABLE IF NOT EXISTS market_regime_snapshots (
  cycle_id TEXT PRIMARY KEY REFERENCES market_state_cycles(cycle_id) ON DELETE CASCADE,
  market_regime TEXT NOT NULL,
  breadth_state TEXT NOT NULL,
  trend_state TEXT NOT NULL,
  liquidity_state TEXT NOT NULL,
  event_pressure_state TEXT NOT NULL,
  confidence DOUBLE PRECISION NOT NULL,
  watchlist_count INTEGER NOT NULL DEFAULT 0,
  reasoning_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_market_state_cycles_created ON market_state_cycles(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ticker_snapshots_cycle_score ON ticker_snapshots(cycle_id, watchlist_score DESC, ticker ASC);
CREATE INDEX IF NOT EXISTS idx_ticker_snapshots_ticker_created ON ticker_snapshots(ticker, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sector_snapshots_cycle_breadth ON sector_snapshots(cycle_id, breadth_pct DESC NULLS LAST, sector ASC);
CREATE INDEX IF NOT EXISTS idx_market_regime_snapshots_created ON market_regime_snapshots(created_at DESC);

COMMIT;
