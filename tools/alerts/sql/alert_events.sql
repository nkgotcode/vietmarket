CREATE TABLE IF NOT EXISTS alert_events (
  id                BIGSERIAL PRIMARY KEY,
  event_id          TEXT UNIQUE NOT NULL,
  event_type        TEXT NOT NULL,
  source            TEXT NOT NULL,
  symbol            TEXT NULL,
  tf                TEXT NULL,
  account_id        TEXT NULL,
  venue             TEXT NULL,
  ts_ns             BIGINT NOT NULL,
  payload           JSONB NOT NULL,
  tags              JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  processing_state  TEXT NOT NULL DEFAULT 'pending',
  attempts          INT NOT NULL DEFAULT 0,
  last_error        TEXT NULL,
  processed_at      TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS idx_alert_events_state_created
  ON alert_events (processing_state, created_at);

CREATE INDEX IF NOT EXISTS idx_alert_events_event_type_created
  ON alert_events (event_type, created_at DESC);
