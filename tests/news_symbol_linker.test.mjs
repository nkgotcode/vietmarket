import test from 'node:test';
import assert from 'node:assert/strict';
import { linkSymbolsFromTitle } from '../lib/news_symbol_linker.mjs';

test('linkSymbolsFromTitle prefers high-confidence patterns', () => {
  const known = new Set(['FPT', 'HPG', 'VNM']);
  const hits = linkSymbolsFromTitle('Cổ phiếu FPT tăng mạnh, HPG (HPG) bứt tốc', known);
  assert.ok(hits.find((x) => x.ticker === 'FPT'));
  assert.ok(hits.find((x) => x.ticker === 'HPG'));
  const hpg = hits.find((x) => x.ticker === 'HPG');
  assert.ok(hpg.confidence >= 0.9);
});
