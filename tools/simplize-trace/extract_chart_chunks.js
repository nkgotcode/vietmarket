#!/usr/bin/env node
/*
Extract dynamic chunk URLs needed by /chart route.
- Parses chart page bundle for n.e(<id>) calls
- Parses webpack runtime o.u mapping to turn chunkId -> relative URL
*/
const fs = require('fs');

const chartFile = process.argv[2] || '/tmp/simplize_crawl/chunks/chart-b8c810043e98f8ab.js';
const runtimeFile = process.argv[3] || '/tmp/simplize_crawl/chunks/webpack-cd26e98fbf2bad0f.js';

const chartSrc = fs.readFileSync(chartFile,'utf8');
const rt = fs.readFileSync(runtimeFile,'utf8');

// find all n.e(12345)
const ids = new Set();
for (const m of chartSrc.matchAll(/\bn\.e\((\d+)\)/g)) ids.add(Number(m[1]));

// Parse runtime mapping: patterns like 32031===e?"static/chunks/"+e+"-hash.js":
const map = new Map();
for (const m of rt.matchAll(/(\d+)===e\?"static\/chunks\/"\+e\+"-([0-9a-f]+)\.js"/g)) {
  map.set(Number(m[1]), `static/chunks/${m[1]}-${m[2]}.js`);
}
// Also: patterns like 10684===e?"static/chunks/"+e+".01dd0bf...js":
for (const m of rt.matchAll(/(\d+)===e\?"static\/chunks\/"\+e\+"\.([0-9a-f]+)\.js"/g)) {
  map.set(Number(m[1]), `static/chunks/${m[1]}.${m[2]}.js`);
}

const resolved = [];
const unresolved = [];
for (const id of [...ids].sort((a,b)=>a-b)) {
  if (map.has(id)) resolved.push({id, path: map.get(id)});
  else unresolved.push(id);
}

process.stdout.write(JSON.stringify({chartFile, runtimeFile, count: ids.size, resolvedCount: resolved.length, unresolvedCount: unresolved.length, resolved, unresolved}, null, 2));
