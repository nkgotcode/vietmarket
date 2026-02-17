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
  const u = process.env.NEXT_PUBLIC_HISTORY_API_URL;
  if (!u) throw new Error('Missing NEXT_PUBLIC_HISTORY_API_URL');
  return u.replace(/\/$/, '');
}

function getApiKey() {
  const k = process.env.NEXT_PUBLIC_HISTORY_API_KEY;
  if (!k) throw new Error('Missing NEXT_PUBLIC_HISTORY_API_KEY');
  return k;
}

export async function fetchCandles(params: {
  ticker: string;
  tf: TF;
  beforeTs?: number;
  limit?: number;
}): Promise<{ rows: HistoryApiCandle[] }>
{
  const { ticker, tf, beforeTs, limit } = params;
  const url = new URL(getBaseUrl() + '/candles');
  url.searchParams.set('ticker', ticker);
  url.searchParams.set('tf', tf);
  if (beforeTs != null) url.searchParams.set('beforeTs', String(beforeTs));
  if (limit != null) url.searchParams.set('limit', String(limit));

  const r = await fetch(url.toString(), {
    headers: {
      'x-api-key': getApiKey(),
    },
    // This is market data; revalidate quickly.
    cache: 'no-store',
  });

  if (!r.ok) {
    const text = await r.text();
    throw new Error(`History API error: ${r.status} ${text.slice(0, 300)}`);
  }

  const j = await r.json();
  return { rows: (j?.rows || []) as HistoryApiCandle[] };
}
