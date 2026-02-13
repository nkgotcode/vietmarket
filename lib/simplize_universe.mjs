const TICKER_RE = /^[A-Z0-9._-]{2,10}$/;

export async function fetchUniverse({ endpoint = 'https://api2.simplize.vn/api/company/separate-share/list-tickers', timeoutMs = 20000 } = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: {
        accept: 'application/json',
        'content-type': 'application/json',
      },
      body: JSON.stringify({}),
      signal: controller.signal,
    });
    const body = await res.json().catch(() => ({}));
    const raw = body?.data;
    const tickers = Array.isArray(raw)
      ? raw
          .map((x) => (typeof x === 'string' ? x : x?.ticker || x?.symbol || null))
          .filter(Boolean)
          .map((x) => String(x).trim().toUpperCase())
      : [];

    const uniq = [...new Set(tickers)].filter((x) => TICKER_RE.test(x));
    return { ok: res.ok, status: res.status, count: uniq.length, tickers: uniq, bodyMessage: body?.message ?? null, source: 'separate-share' };
  } finally {
    clearTimeout(timer);
  }
}

export async function fetchUniverseFromSearch({
  endpoint = 'https://api2.simplize.vn/api/search/company/suggestions',
  alphabet = 'abcdefghijklmnopqrstuvwxyz0123456789',
  timeoutMs = 12000,
} = {}) {
  const tickers = new Set();
  let requests = 0;

  for (const ch of alphabet) {
    requests += 1;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const url = `${endpoint}?q=${encodeURIComponent(ch)}`;
      const res = await fetch(url, {
        method: 'GET',
        headers: { accept: 'application/json' },
        signal: controller.signal,
      });
      const body = await res.json().catch(() => ({}));
      const items = Array.isArray(body?.data) ? body.data : [];
      for (const it of items) {
        const tk = String(it?.ticker || '').trim().toUpperCase();
        if (TICKER_RE.test(tk)) tickers.add(tk);
      }
    } catch {
      // continue
    } finally {
      clearTimeout(timer);
    }
  }

  const list = [...tickers].sort();
  return { ok: true, source: 'search-suggestions', requests, count: list.length, tickers: list };
}

export function chunk(array, size) {
  const out = [];
  for (let i = 0; i < array.length; i += size) out.push(array.slice(i, i + size));
  return out;
}
