#!/usr/bin/env node

import { spawn } from 'node:child_process';
import { openSync } from 'node:fs';
import { readFile, writeFile, unlink, mkdir } from 'node:fs/promises';
import path from 'node:path';

function parseArgs(argv) {
  const out = {
    cmd: 'status',
    port: 18991,
    source: 'data/simplize/publish/latest.json',
    dbFile: 'data/simplize/simplize.db',
    registryDbFile: 'data/registry/market_registry.db',
    pidFile: 'tmp/simplize-api.pid',
    logFile: 'tmp/simplize-api.log',
  };

  const [cmd, ...rest] = argv;
  if (cmd && !cmd.startsWith('-')) out.cmd = cmd;

  for (let i = 0; i < rest.length; i++) {
    const a = rest[i];
    const v = rest[i + 1];
    if (a === '--port') {
      out.port = Number(v || out.port);
      i++;
    } else if (a === '--source') {
      out.source = String(v || out.source);
      i++;
    } else if (a === '--db-file') {
      out.dbFile = String(v || out.dbFile);
      i++;
    } else if (a === '--registry-db-file') {
      out.registryDbFile = String(v || out.registryDbFile);
      i++;
    } else if (a === '--pid-file') {
      out.pidFile = String(v || out.pidFile);
      i++;
    } else if (a === '--log-file') {
      out.logFile = String(v || out.logFile);
      i++;
    } else if (a === '--help' || a === '-h') {
      printHelp();
      process.exit(0);
    }
  }

  return out;
}

function printHelp() {
  console.log(
`Usage:
  node scripts/simplize_api_daemon.mjs <start|stop|restart|status>

Options:
  --port <n>         API port (default: 18991)
  --source <file>    Publish JSON source (default: data/simplize/publish/latest.json)
  --db-file <file>   SQLite DB file (default: data/simplize/simplize.db)
  --registry-db-file <file> Registry DB file (default: data/registry/market_registry.db)
  --pid-file <file>  PID file (default: tmp/simplize-api.pid)
  --log-file <file>  Log file (default: tmp/simplize-api.log)
`
  );
}

async function readPid(pidFile) {
  try {
    const s = (await readFile(pidFile, 'utf8')).trim();
    const n = Number(s);
    return Number.isFinite(n) ? n : null;
  } catch {
    return null;
  }
}

function isAlive(pid) {
  if (!pid) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

async function start(opts) {
  const pidPath = path.resolve(opts.pidFile);
  const logPath = path.resolve(opts.logFile);
  const source = path.resolve(opts.source);
  const dbFile = path.resolve(opts.dbFile);
  const registryDbFile = path.resolve(opts.registryDbFile);

  await mkdir(path.dirname(pidPath), { recursive: true });
  await mkdir(path.dirname(logPath), { recursive: true });

  const existing = await readPid(pidPath);
  if (isAlive(existing)) {
    return { ok: true, alreadyRunning: true, pid: existing, pidFile: pidPath, logFile: logPath };
  }

  const outFd = openSync(logPath, 'a');
  const stdio = ['ignore', outFd, outFd];

  const child = spawn(process.execPath, [
    path.resolve('scripts/simplize_api.mjs'),
    '--port',
    String(opts.port),
    '--source',
    source,
    '--db-file',
    dbFile,
    '--registry-db-file',
    registryDbFile,
  ], {
    cwd: process.cwd(),
    detached: true,
    stdio,
  });

  child.unref();
  await writeFile(pidPath, String(child.pid), 'utf8');

  return { ok: true, started: true, pid: child.pid, pidFile: pidPath, logFile: logPath, port: opts.port };
}

async function stop(opts) {
  const pidPath = path.resolve(opts.pidFile);
  const pid = await readPid(pidPath);
  if (!pid || !isAlive(pid)) {
    try { await unlink(pidPath); } catch {}
    return { ok: true, alreadyStopped: true };
  }

  try {
    process.kill(pid, 'SIGTERM');
  } catch {}

  await new Promise((r) => setTimeout(r, 300));
  if (isAlive(pid)) {
    try { process.kill(pid, 'SIGKILL'); } catch {}
  }

  try { await unlink(pidPath); } catch {}
  return { ok: true, stopped: true, pid };
}

async function status(opts) {
  const pidPath = path.resolve(opts.pidFile);
  const logPath = path.resolve(opts.logFile);
  const pid = await readPid(pidPath);
  const running = isAlive(pid);
  return { ok: true, running, pid: running ? pid : null, pidFile: pidPath, logFile: logPath, port: opts.port };
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));

  let result;
  if (opts.cmd === 'start') result = await start(opts);
  else if (opts.cmd === 'stop') result = await stop(opts);
  else if (opts.cmd === 'restart') {
    await stop(opts);
    result = await start(opts);
  } else if (opts.cmd === 'status') result = await status(opts);
  else {
    throw new Error(`Unknown command: ${opts.cmd}`);
  }

  console.log(JSON.stringify(result, null, 2));
}

main().catch((err) => {
  console.error(err.stack || err.message || String(err));
  process.exit(1);
});
