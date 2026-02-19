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
export type NewsRow = { url: string; title: string; source: string; published_at: string | null; tickers?: string[]; snippet?: string | null };

export type V1Envelope<T> = { ok: boolean; version: 'v1'; data: T };

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

export type NewsCursor = { beforePublishedAt: string | null; beforeUrl: string };

export async function fetchNewsLatest(params: { limit?: number; cursor?: NewsCursor | null } = {}): Promise<{ rows: NewsRow[]; nextCursor: NewsCursor | null }> {
  const url = new URL('/api/history/news/latest', window.location.origin);
  if (params.limit != null) url.searchParams.set('limit', String(params.limit));
  if (params.cursor?.beforePublishedAt) url.searchParams.set('beforePublishedAt', params.cursor.beforePublishedAt);
  if (params.cursor?.beforeUrl) url.searchParams.set('beforeUrl', params.cursor.beforeUrl);

  const r = await fetch(url.toString(), { cache: 'no-store' });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`History API error: ${r.status} ${text.slice(0, 300)}`);
  }

  const j = await r.json();
  return { rows: (j?.rows || []) as NewsRow[], nextCursor: (j?.nextCursor || null) as NewsCursor | null };
}

export async function fetchNewsByTicker(params: { ticker: string; limit?: number; cursor?: NewsCursor | null }): Promise<{ rows: NewsRow[]; nextCursor: NewsCursor | null }> {
  const url = new URL('/api/history/news/by-ticker', window.location.origin);
  url.searchParams.set('ticker', params.ticker);
  if (params.limit != null) url.searchParams.set('limit', String(params.limit));
  if (params.cursor?.beforePublishedAt) url.searchParams.set('beforePublishedAt', params.cursor.beforePublishedAt);
  if (params.cursor?.beforeUrl) url.searchParams.set('beforeUrl', params.cursor.beforeUrl);

  const r = await fetch(url.toString(), { cache: 'no-store' });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`History API error: ${r.status} ${text.slice(0, 300)}`);
  }

  const j = await r.json();
  return { rows: (j?.rows || []) as NewsRow[], nextCursor: (j?.nextCursor || null) as NewsCursor | null };
}

async function fetchV1<T>(path: string): Promise<T> {
  const url = new URL(path, window.location.origin);
  const r = await fetch(url.toString(), { cache: 'no-store' });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`History API error: ${r.status} ${text.slice(0, 300)}`);
  }
  const j = (await r.json()) as V1Envelope<T>;
  return j?.data as T;
}

export async function fetchAnalyticsOverview() {
  return fetchV1<any>('/api/analytics/overview');
}

export async function fetchOverallHealth() {
  return fetchV1<any>('/api/overall/health');
}

export async function fetchSentimentOverview(params: { windowDays?: number; limit?: number } = {}) {
  const q = new URL('/api/sentiment/overview', window.location.origin);
  if (params.windowDays != null) q.searchParams.set('windowDays', String(params.windowDays));
  if (params.limit != null) q.searchParams.set('limit', String(params.limit));
  return fetchV1<any>(q.pathname + q.search);
}

export async function fetchTickerSentiment(ticker: string, params: { windowDays?: number } = {}) {
  const q = new URL(`/api/sentiment/${encodeURIComponent(ticker)}`, window.location.origin);
  if (params.windowDays != null) q.searchParams.set('windowDays', String(params.windowDays));
  return fetchV1<any>(q.pathname + q.search);
}

export async function fetchTickerContext(ticker: string) {
  return fetchV1<any>(`/api/context/${encodeURIComponent(ticker)}`);
}
