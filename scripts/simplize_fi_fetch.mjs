#!/usr/bin/env node

/**
 * Simplize FI fetcher (public endpoints focus)
 *
 * Usage:
 *   node scripts/simplize_fi_fetch.mjs --ticker FPT --period Q --size 12
 *   node scripts/simplize_fi_fetch.mjs -t FPT -p Y -s 8 --pretty
 */

import { writeFile } from 'node:fs/promises';

const BASE = 'https://api2.simplize.vn';

function parseArgs(argv) {
  const out = {
    ticker: 'FPT',
    tickers: null,
    period: 'Q',
    size: 12,
    pretty: true,
    save: null,
  };

  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const v = argv[i + 1];
    if (a === '--ticker' || a === '-t') {
      out.ticker = String(v || '').toUpperCase();
      i++;
    } else if (a === '--tickers') {
      out.tickers = String(v || '')
        .split(',')
        .map((x) => x.trim().toUpperCase())
        .filter(Boolean);
      i++;
    } else if (a === '--period' || a === '-p') {
      out.period = String(v || '').toUpperCase();
      i++;
    } else if (a === '--size' || a === '-s') {
      out.size = Number(v || 12);
      i++;
    } else if (a === '--save') {
      out.save = String(v || '').trim() || null;
      i++;
    } else if (a === '--pretty') {
      out.pretty = true;
    } else if (a === '--compact') {
      out.pretty = false;
    } else if (a === '--help' || a === '-h') {
      printHelp();
      process.exit(0);
    }
  }

  if (out.tickers && out.tickers.length > 0) {
    out.ticker = out.tickers[0];
  }

  if (!out.ticker) throw new Error('ticker is required');
  if (!['Q', 'Y'].includes(out.period)) {
    throw new Error('period must be Q or Y');
  }
  if (!Number.isFinite(out.size) || out.size <= 0) {
    throw new Error('size must be > 0');
  }

  return out;
}

function printHelp() {
  console.log(`Simplize FI fetcher\n\n` +
`Options:\n` +
`  -t, --ticker <SYMBOL>   Stock ticker (default: FPT)\n` +
`  -p, --period <Q|Y>      Period: Q (quarter) or Y (year) (default: Q)\n` +
`  -s, --size <N>          Number of rows (default: 12)\n` +
`      --tickers <A,B,C>   Batch mode: comma-separated tickers\n` +
`      --save <file>       Save output JSON to file\n` +
`      --pretty            Pretty JSON output (default)\n` +
`      --compact           Compact JSON output\n` +
`  -h, --help              Show this help\n`);
}

async function request(path) {
  const url = `${BASE}${path}`;
  const res = await fetch(url, {
    headers: {
      'accept': 'application/json',
      'content-type': 'application/json',
    },
  });

  let body;
  try {
    body = await res.json();
  } catch {
    body = { raw: await res.text() };
  }

  return {
    ok: res.ok,
    status: res.status,
    url,
    body,
  };
}

function summarizeEndpoint(result) {
  const msg = result?.body?.message || null;
  const hasData = result?.body?.data !== undefined;
  const itemCount = Array.isArray(result?.body?.data?.items)
    ? result.body.data.items.length
    : Array.isArray(result?.body?.data)
      ? result.body.data.length
      : null;

  return {
    status: result.status,
    ok: result.ok,
    message: msg,
    hasData,
    itemCount,
  };
}

async function fetchTickerBlock({ ticker, period, size }) {
  const paths = {
    periodSelect: `/api/company/fi/period/select/${ticker}?period=${period}`,
    structureOverview: `/api/company/fi/structure/overview/${ticker}?period=${period}`,
    aggCompareOverview: `/api/company/fi/agg-compare/overview/${ticker}?period=${period}`,
    is: `/api/company/fi/is/${ticker}?type=null&period=${period}&size=${size}`,
    bs: `/api/company/fi/bs/${ticker}?type=null&period=${period}&size=${size}`,
    cf: `/api/company/fi/cf/${ticker}?period=${period}&size=${size}`,
    ratio: `/api/company/fi/ratio/${ticker}?period=${period}&size=${size}`,
  };

  const entries = await Promise.all(
    Object.entries(paths).map(async ([key, path]) => [key, await request(path)])
  );

  const raw = Object.fromEntries(entries);
  const summary = Object.fromEntries(
    Object.entries(raw).map(([k, v]) => [k, summarizeEndpoint(v)])
  );

  return {
    summary,
    data: Object.fromEntries(
      Object.entries(raw).map(([k, v]) => [
        k,
        {
          status: v.status,
          ok: v.ok,
          url: v.url,
          body: v.body,
        },
      ])
    ),
  };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const { ticker, tickers, period, size, pretty, save } = args;
  const tickerList = tickers && tickers.length ? tickers : [ticker];

  const batchEntries = await Promise.all(
    tickerList.map(async (tk) => [tk, await fetchTickerBlock({ ticker: tk, period, size })])
  );
  const batch = Object.fromEntries(batchEntries);

  const output = {
    input: { ticker, tickers: tickerList, period, size },
    note:
      period === 'Y'
        ? 'Yearly statement endpoints may require auth (401 on is/bs/cf/ratio), while periodSelect can still return options.'
        : 'Quarterly endpoints are generally public for supported tickers.',
    batch,
  };

  const json = JSON.stringify(output, null, pretty ? 2 : 0);
  if (save) {
    await writeFile(save, json + '\n', 'utf8');
  }
  process.stdout.write(json + '\n');
}

main().catch((err) => {
  console.error(`Error: ${err.message}`);
  process.exit(1);
});
