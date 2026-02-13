const STOPWORDS = new Set(['ETF','USD','VND','VNINDEX','HNX','HOSE','UPCOM','CTCP','VNI']);

function validTicker(tk) {
  return /^[A-Z]{2,5}$/.test(tk) && !STOPWORDS.has(tk);
}

function addHit(map, ticker, confidence, method) {
  const prev = map.get(ticker);
  if (!prev || confidence > prev.confidence) {
    map.set(ticker, { ticker, confidence, method });
  }
}

export function linkSymbolsFromTitle(title, knownTickers = null) {
  const text = String(title || '');
  const up = text.toUpperCase();
  const hits = new Map();

  // (FPT)
  for (const m of up.matchAll(/\(([A-Z]{2,5})\)/g)) {
    const tk = m[1];
    if (!validTicker(tk)) continue;
    if (knownTickers && !knownTickers.has(tk)) continue;
    addHit(hits, tk, 0.95, 'title_paren');
  }

  // cổ phiếu FPT / mã FPT
  for (const m of up.matchAll(/(?:CỔ\s*PHIẾU|MA\s*|MÃ\s*)([A-Z]{2,5})/g)) {
    const tk = m[1];
    if (!validTicker(tk)) continue;
    if (knownTickers && !knownTickers.has(tk)) continue;
    addHit(hits, tk, 0.9, 'title_keyword');
  }

  // generic uppercase token fallback
  for (const m of up.matchAll(/\b([A-Z]{2,5})\b/g)) {
    const tk = m[1];
    if (!validTicker(tk)) continue;
    if (knownTickers && !knownTickers.has(tk)) continue;
    addHit(hits, tk, 0.6, 'title_token');
  }

  return [...hits.values()].sort((a, b) => b.confidence - a.confidence || a.ticker.localeCompare(b.ticker));
}
