import test from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { setTimeout as delay } from 'node:timers/promises';

const BASE = process.env.CONTRACT_BASE_URL || 'http://127.0.0.1:18787';
const API_KEY = process.env.CONTRACT_API_KEY || 'test-key';
const PG_URL = process.env.CONTRACT_PG_URL || 'postgres://postgres:postgres@127.0.0.1:15432/postgres';

let server;

async function waitForHealthy(retries = 60) {
  for (let i = 0; i < retries; i++) {
    try {
      const r = await fetch(`${BASE}/healthz`);
      if (r.ok) return;
    } catch {}
    await delay(250);
  }
  throw new Error('history-api failed healthz check');
}

async function getJson(path) {
  const r = await fetch(`${BASE}${path}`, {
    headers: { 'x-api-key': API_KEY },
  });
  const text = await r.text();
  let body = null;
  try {
    body = JSON.parse(text);
  } catch {
    throw new Error(`Non-JSON response for ${path}: ${text.slice(0, 300)}`);
  }
  return { status: r.status, body };
}

test.before(async () => {
  server = spawn('node', ['server.mjs'], {
    cwd: new URL('..', import.meta.url),
    env: {
      ...process.env,
      PORT: '18787',
      API_KEY,
      PG_URL,
      PG_POOL_MAX: '2',
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  server.stdout.on('data', () => {});
  server.stderr.on('data', () => {});

  await waitForHealthy();
});

test.after(async () => {
  if (server && !server.killed) {
    server.kill('SIGTERM');
    await delay(200);
    if (!server.killed) server.kill('SIGKILL');
  }
});

test('GET /v1/analytics/overview contract', async () => {
  const { status, body } = await getJson('/v1/analytics/overview');
  assert.equal(status, 200);
  assert.equal(body.ok, true);
  assert.equal(body.version, 'v1');
  assert.ok(body.data);
  assert.equal(typeof body.data.candles_rows, 'number');
  assert.equal(typeof body.data.candles_tickers, 'number');
  assert.ok('coverage_pct' in body.data);
});

test('GET /v1/context/:ticker contract', async () => {
  const { status, body } = await getJson('/v1/context/VCB');
  assert.equal(status, 200);
  assert.equal(body.ok, true);
  assert.equal(body.version, 'v1');
  assert.equal(body.data?.ticker, 'VCB');
  assert.ok(body.data?.candles_latest);
  assert.ok(Array.isArray(body.data?.fundamentals));
  assert.ok(Array.isArray(body.data?.news));
});

test('GET /v1/sentiment/overview contract', async () => {
  const { status, body } = await getJson('/v1/sentiment/overview?windowDays=30&limit=10');
  assert.equal(status, 200);
  assert.equal(body.ok, true);
  assert.equal(body.version, 'v1');
  assert.equal(body.data?.window_days, 30);
  assert.ok(body.data?.overall);
  assert.ok(Array.isArray(body.data?.top_positive));
  assert.ok(Array.isArray(body.data?.top_negative));
});

test('GET /v1/sentiment/:ticker contract', async () => {
  const { status, body } = await getJson('/v1/sentiment/VCB?windowDays=30');
  assert.equal(status, 200);
  assert.equal(body.ok, true);
  assert.equal(body.version, 'v1');
  assert.equal(body.data?.ticker, 'VCB');
  assert.equal(body.data?.window_days, 30);
  assert.ok(body.data?.summary);
  assert.ok(Array.isArray(body.data?.recent_articles));
});

test('GET /v1/overall/health contract', async () => {
  const { status, body } = await getJson('/v1/overall/health');
  assert.equal(status, 200);
  assert.equal(body.ok, true);
  assert.equal(body.version, 'v1');
  assert.ok(body.data?.candles);
  assert.ok(body.data?.coverage);
  assert.ok(body.data?.repair_queue);
  assert.ok(body.data?.frontier);
});

test('v1 endpoint auth + validation errors are stable', async () => {
  const unauth = await fetch(`${BASE}/v1/context/VCB`);
  assert.equal(unauth.status, 401);
  const unauthBody = await unauth.json();
  assert.equal(unauthBody.error, 'unauthorized');

  const badTicker = await fetch(`${BASE}/v1/context/@@@`, { headers: { 'x-api-key': API_KEY } });
  assert.equal(badTicker.status, 400);
  const badTickerBody = await badTicker.json();
  assert.equal(badTickerBody.error, 'invalid_ticker');

  const badWindow = await fetch(`${BASE}/v1/sentiment/overview?windowDays=0`, { headers: { 'x-api-key': API_KEY } });
  assert.equal(badWindow.status, 400);
  const badWindowBody = await badWindow.json();
  assert.equal(badWindowBody.error, 'invalid_window_days');
});
