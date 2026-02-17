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

export async function fetchCandles(params: {
  ticker: string;
  tf: TF;
  beforeTs?: number;
  limit?: number;
}): Promise<{ rows: HistoryApiCandle[] }>
{
  const { ticker, tf, beforeTs, limit } = params;
  const url = new URL('/api/history/candles', window.location.origin);
  url.searchParams.set('ticker', ticker);
  url.searchParams.set('tf', tf);
  if (beforeTs != null) url.searchParams.set('beforeTs', String(beforeTs));
  if (limit != null) url.searchParams.set('limit', String(limit));

  const r = await fetch(url.toString(), {
    // This is market data; always fetch fresh.
    cache: 'no-store',
  });

  if (!r.ok) {
    const text = await r.text();
    throw new Error(`History API error: ${r.status} ${text.slice(0, 300)}`);
  }

  const j = await r.json();
  return { rows: (j?.rows || []) as HistoryApiCandle[] };
}
