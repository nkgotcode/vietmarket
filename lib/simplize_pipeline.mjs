import crypto from 'node:crypto';
import { fetchJsonWithRetry } from './simplize_client.mjs';

const BASE = 'https://api2.simplize.vn';

function endpointMap({ ticker, period, size }) {
  return {
    periodSelect: `/api/company/fi/period/select/${ticker}?period=${period}`,
    structureOverview: `/api/company/fi/structure/overview/${ticker}?period=${period}`,
    aggCompareOverview: `/api/company/fi/agg-compare/overview/${ticker}?period=${period}`,
    is: `/api/company/fi/is/${ticker}?type=null&period=${period}&size=${size}`,
    bs: `/api/company/fi/bs/${ticker}?type=null&period=${period}&size=${size}`,
    cf: `/api/company/fi/cf/${ticker}?period=${period}&size=${size}`,
    ratio: `/api/company/fi/ratio/${ticker}?period=${period}&size=${size}`,
  };
}

export async function fetchTickerBlock({ ticker, period = 'Q', size = 12, requestOptions = {} }) {
  const paths = endpointMap({ ticker, period, size });
  const entries = await Promise.all(
    Object.entries(paths).map(async ([k, p]) => [k, await fetchJsonWithRetry(`${BASE}${p}`, requestOptions)])
  );

  const data = Object.fromEntries(entries);
  const summary = Object.fromEntries(
    Object.entries(data).map(([k, v]) => [k, {
      ok: v.ok,
      status: v.status,
      message: v?.body?.message ?? null,
      hasData: v?.body?.data !== undefined,
    }])
  );

  return {
    ticker,
    period,
    size,
    fetchedAt: new Date().toISOString(),
    summary,
    data,
  };
}

export function stableStringify(obj) {
  if (obj === null || typeof obj !== 'object') return JSON.stringify(obj);
  if (Array.isArray(obj)) return `[${obj.map(stableStringify).join(',')}]`;
  const keys = Object.keys(obj).sort();
  return `{${keys.map((k) => `${JSON.stringify(k)}:${stableStringify(obj[k])}`).join(',')}}`;
}

export function blockHash(block) {
  return crypto.createHash('sha256').update(stableStringify(block)).digest('hex');
}

function extractMetrics(item, statement) {
  const rows = [];
  for (const [k, v] of Object.entries(item)) {
    if (typeof v !== 'number' || Number.isNaN(v)) continue;
    if (!/^(is\d+|bs\d+|cf\d+|r\d+|ratio\d+)$/i.test(k)) continue;
    rows.push({ metric: k, value: v, statement });
  }
  return rows;
}

export function normalizeBlock(block) {
  const out = [];
  const fetchedAt = block.fetchedAt;
  const ticker = block.ticker;
  const period = block.period;

  for (const statement of ['is', 'bs', 'cf', 'ratio']) {
    const items = block?.data?.[statement]?.body?.data?.items;
    if (!Array.isArray(items)) continue;

    for (const item of items) {
      const periodDate = item.periodDate ?? null;
      const periodDateName = item.periodDateName ?? null;
      const metrics = extractMetrics(item, statement);
      for (const m of metrics) {
        out.push({
          ticker,
          period,
          statement,
          periodDate,
          periodDateName,
          metric: m.metric,
          value: m.value,
          fetchedAt,
        });
      }
    }
  }

  return out;
}
