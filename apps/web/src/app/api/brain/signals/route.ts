import { NextResponse } from 'next/server';

import { requireAppAuth } from '@/lib/authz';
import { getPgPool } from '@/lib/pg';

export async function GET(req: Request) {
  const denied = await requireAppAuth(req);
  if (denied) return denied;

  const pool = getPgPool();
  const cycleResult = await pool.query(
    `SELECT cycle_id, overall_status, freshness_status, frontier_status, universe_count, regime_code, notes_json, created_at
       FROM market_state_cycles
      ORDER BY created_at DESC
      LIMIT 1`
  );

  if (cycleResult.rows.length === 0) {
    return NextResponse.json({ ok: true, cycle: null, rows: [] });
  }

  const cycle = cycleResult.rows[0];
  const candidateResult = await pool.query(
    `SELECT c.ticker, c.total_score, c.total_confidence, c.ranking_bucket, c.blocking_flag,
            c.ranking_reason_json,
            t.exchange, t.sector, t.watchlist_score,
            t.snapshot_json->>'industry_name' AS industry_name,
            t.snapshot_json->>'icb_code' AS icb_code,
            t.snapshot_json->>'industry_code' AS industry_code
       FROM candidate_rankings c
       JOIN ticker_snapshots t
         ON t.cycle_id = c.cycle_id AND t.ticker = c.ticker
      WHERE c.cycle_id = $1
      ORDER BY c.blocking_flag ASC, c.total_score DESC, c.total_confidence DESC, c.ticker ASC
      LIMIT 25`,
    [cycle.cycle_id]
  );

  const scoreResult = await pool.query(
    `SELECT cycle_id, ticker, signal_family, score_raw, score_normalized, confidence,
            horizon, expires_at, blocking_flag, reason_json, created_at
       FROM signal_scores
      WHERE cycle_id = $1
      ORDER BY ticker ASC, signal_family ASC`,
    [cycle.cycle_id]
  );

  const componentResult = await pool.query(
    `SELECT cycle_id, ticker, signal_family, component_name, component_value,
            component_weight, component_note, created_at
       FROM signal_components
      WHERE cycle_id = $1
      ORDER BY ticker ASC, signal_family ASC, component_name ASC`,
    [cycle.cycle_id]
  );

  const componentsByKey = new Map<string, Array<Record<string, unknown>>>();
  for (const row of componentResult.rows) {
    const key = `${row.ticker}::${row.signal_family}`;
    const items = componentsByKey.get(key) ?? [];
    items.push(row);
    componentsByKey.set(key, items);
  }

  const scoresByTicker = new Map<string, Array<Record<string, unknown>>>();
  for (const row of scoreResult.rows) {
    const key = row.ticker as string;
    const items = scoresByTicker.get(key) ?? [];
    items.push({
      ...row,
      components: componentsByKey.get(`${row.ticker}::${row.signal_family}`) ?? [],
    });
    scoresByTicker.set(key, items);
  }

  const rows = candidateResult.rows.map((row) => ({
    ...row,
    signals: scoresByTicker.get(row.ticker) ?? [],
  }));

  return NextResponse.json({ ok: true, cycle, rows });
}
