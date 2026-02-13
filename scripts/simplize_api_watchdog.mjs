#!/usr/bin/env node

import { spawnSync } from 'node:child_process';

function parseArgs(argv) {
  const out = { port: 18991 };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const v = argv[i + 1];
    if (a === '--port') { out.port = Number(v || out.port); i++; }
  }
  return out;
}

async function check(port) {
  try {
    const res = await fetch(`http://127.0.0.1:${port}/health`, { signal: AbortSignal.timeout(2500) });
    if (!res.ok) return false;
    const body = await res.json().catch(() => ({}));
    return Boolean(body?.ok);
  } catch {
    return false;
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const ok = await check(args.port);
  if (ok) {
    console.log(JSON.stringify({ ok: true, action: 'none', reason: 'healthy' }));
    return;
  }

  const r = spawnSync(process.execPath, ['scripts/simplize_api_daemon.mjs', 'restart', '--port', String(args.port)], {
    cwd: process.cwd(),
    encoding: 'utf8',
    timeout: 30000,
  });

  if (r.status !== 0) {
    console.log(JSON.stringify({ ok: false, action: 'restart_failed', stderr: r.stderr?.slice(0, 300) || null }));
    process.exit(2);
  }

  const okAfter = await check(args.port);
  console.log(JSON.stringify({ ok: okAfter, action: 'restart', restarted: true }));
  if (!okAfter) process.exit(3);
}

main().catch((err) => {
  console.error(err.stack || err.message || String(err));
  process.exit(1);
});
