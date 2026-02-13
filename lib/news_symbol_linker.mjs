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

function linkSymbolsCore(text, knownTickers, prefix) {
  const up = String(text || '').toUpperCase();
  const hits = new Map();

  // (FPT)
  for (const m of up.matchAll(/\(([A-Z]{2,5})\)/g)) {
    const tk = m[1];
    if (!validTicker(tk)) continue;
    if (knownTickers && !knownTickers.has(tk)) continue;
    addHit(hits, tk, 0.95, `${prefix}paren`);
  }

  // FPT (HOSE) / FPT (HNX) / FPT (UPCOM)
  for (const m of up.matchAll(/\b([A-Z]{2,5})\s*\((HOSE|HNX|UPCOM)\)\b/g)) {
    const tk = m[1];
    if (!validTicker(tk)) continue;
    if (knownTickers && !knownTickers.has(tk)) continue;
    addHit(hits, tk, 0.92, `${prefix}exchange_paren`);
  }

  // HOSE: FPT / HNX: SHB / UPCOM: BVB
  for (const m of up.matchAll(/\b(HOSE|HNX|UPCOM)\s*[:\-]\s*([A-Z]{2,5})\b/g)) {
    const tk = m[2];
    if (!validTicker(tk)) continue;
    if (knownTickers && !knownTickers.has(tk)) continue;
    addHit(hits, tk, 0.92, `${prefix}exchange_colon`);
  }

  // cổ phiếu FPT / mã FPT / mã CK FPT / mã chứng khoán FPT
  for (const m of up.matchAll(/(?:CỔ\s*PHIẾU|MÃ\s*(?:CK\s*)?|MÃ\s*CHỨNG\s*KHOÁN\s*)([A-Z]{2,5})/g)) {
    const tk = m[1];
    if (!validTicker(tk)) continue;
    if (knownTickers && !knownTickers.has(tk)) continue;
    addHit(hits, tk, 0.9, `${prefix}keyword`);
  }

  // generic uppercase token fallback
  for (const m of up.matchAll(/\b([A-Z]{2,5})\b/g)) {
    const tk = m[1];
    if (!validTicker(tk)) continue;
    if (knownTickers && !knownTickers.has(tk)) continue;
    addHit(hits, tk, 0.6, `${prefix}token`);
  }

  return hits;
}

function finalize(hits) {
  return [...hits.values()].sort((a, b) => b.confidence - a.confidence || a.ticker.localeCompare(b.ticker));
}

export function linkSymbolsFromTitle(title, knownTickers = null) {
  return finalize(linkSymbolsCore(title, knownTickers, 'title_'));
}

export function linkSymbolsFromText(text, knownTickers = null) {
  return finalize(linkSymbolsCore(text, knownTickers, 'body_'));
}
