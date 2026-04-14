BEGIN;

ALTER TABLE symbols
  ADD COLUMN IF NOT EXISTS icb_code TEXT NULL,
  ADD COLUMN IF NOT EXISTS industry_code TEXT NULL,
  ADD COLUMN IF NOT EXISTS sector_name TEXT NULL,
  ADD COLUMN IF NOT EXISTS industry_name TEXT NULL,
  ADD COLUMN IF NOT EXISTS classification_source TEXT NULL,
  ADD COLUMN IF NOT EXISTS classification_updated_at TIMESTAMPTZ NULL;

CREATE INDEX IF NOT EXISTS idx_symbols_sector_name ON symbols(sector_name);
CREATE INDEX IF NOT EXISTS idx_symbols_industry_name ON symbols(industry_name);
CREATE INDEX IF NOT EXISTS idx_symbols_icb_code ON symbols(icb_code);

COMMIT;
