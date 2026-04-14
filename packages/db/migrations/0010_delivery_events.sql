BEGIN;

CREATE TABLE IF NOT EXISTS delivery_events (
  delivery_id TEXT PRIMARY KEY,
  delivery_kind TEXT NOT NULL,
  channel TEXT NOT NULL,
  delivery_status TEXT NOT NULL,
  target_ref TEXT NULL,
  payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  response_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_delivery_events_kind_created
  ON delivery_events(delivery_kind, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_delivery_events_status_created
  ON delivery_events(delivery_status, created_at DESC);

COMMIT;
