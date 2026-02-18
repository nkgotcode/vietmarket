export type TF = '1d' | '1h' | '15m';

export type HistoryApiCandle = {
  ts: number; // unix ms
  o: number | null;
  h: number | null;
  l: number | null;
  c: number | null;
  v: number | null;
  source: string | null;
};

function getBaseUrl() {
  // We proxy through Next.js Route Handler so the API key stays server-side.
  // This route is protected by Clerk auth.
  return '';
}

function getApiKey() {
  // API key is server-side only; browser never sees it.
  return '';
}

export type LatestRow = { ticker: string; tf: TF; ts: number; c: number | null; o: number | null; h: number | null; l: number | null; v: number | null; source: string | null; ingested_at: string | null };
export type TopMoverRow = { ticker: string; tf: TF; ts_latest: number; close_latest: number | null; close_prev: number | null; pct_change: number | null };

export async function fetchCandles(params: {
  ticker: string;
  tf: TF;
  beforeTs?: number;
  limit?: number;
}): Promise<{ rows: HistoryApiCandle[] }> {
  const { ticker, tf, beforeTs, limit } = params;
  const url = new URL('/api/history/candles', window.location.origin);
  url.searchParams.set('ticker', ticker);
  url.searchParams.set('tf', tf);
  if (beforeTs != null) url.searchParams.set('beforeTs', String(beforeTs));
  if (limit != null) url.searchParams.set('limit', String(limit));

  const r = await fetch(url.toString(), { cache: 'no-store' });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`History API error: ${r.status} ${text.slice(0, 300)}`);
  }

  const j = await r.json();
  return { rows: (j?.rows || []) as HistoryApiCandle[] };
}

export async function fetchLatest(params: { tf: TF; limit?: number }): Promise<{ rows: LatestRow[] }> {
  const url = new URL('/api/history/latest', window.location.origin);
  url.searchParams.set('tf', params.tf);
  if (params.limit != null) url.searchParams.set('limit', String(params.limit));

  const r = await fetch(url.toString(), { cache: 'no-store' });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`History API error: ${r.status} ${text.slice(0, 300)}`);
  }

  const j = await r.json();
  return { rows: (j?.rows || []) as LatestRow[] };
}

export async function fetchTopMovers(params: { tf: TF; limit?: number }): Promise<{ rows: TopMoverRow[] }> {
  const url = new URL('/api/history/top-movers', window.location.origin);
  url.searchParams.set('tf', params.tf);
  if (params.limit != null) url.searchParams.set('limit', String(params.limit));

  const r = await fetch(url.toString(), { cache: 'no-store' });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`History API error: ${r.status} ${text.slice(0, 300)}`);
  }

  const j = await r.json();
  return { rows: (j?.rows || []) as TopMoverRow[] };
}
