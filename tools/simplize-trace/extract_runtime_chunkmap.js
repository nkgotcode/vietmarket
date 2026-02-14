#!/usr/bin/env node
/* Extract chunkId -> relative JS path from Next/Webpack runtime (webpack-*.js). */
const fs = require('fs');
const rtFile = process.argv[2] || '/tmp/simplize_crawl/chunks/webpack-cd26e98fbf2bad0f.js';
const src = fs.readFileSync(rtFile,'utf8');

function parsePairs(objText){
  // objText like 74:"abc",285:"def"...
  const map = new Map();
  const re = /(\d+)\s*:\s*"([0-9a-f]+)"/g;
  for(const m of objText.matchAll(re)) map.set(Number(m[1]), m[2]);
  return map;
}

const out = new Map();

// direct ternary mappings with -hash (dynamic id in path)
for (const m of src.matchAll(/(\d+)===e\?"static\/chunks\/"\+e\+"-([0-9a-f]+)\.js"/g)) {
  out.set(Number(m[1]), `static/chunks/${m[1]}-${m[2]}.js`);
}
// direct ternary mappings with -hash (hardcoded id in path)
for (const m of src.matchAll(/(\d+)===e\?"static\/chunks\/(\d+)-([0-9a-f]+)\.js"/g)) {
  const id = Number(m[1]);
  out.set(id, `static/chunks/${m[2]}-${m[3]}.js`);
}
// direct ternary mappings with .hash (dynamic id in path)
for (const m of src.matchAll(/(\d+)===e\?"static\/chunks\/"\+e\+"\.([0-9a-f]+)\.js"/g)) {
  out.set(Number(m[1]), `static/chunks/${m[1]}.${m[2]}.js`);
}
// direct ternary mappings with .hash (hardcoded id in path)
for (const m of src.matchAll(/(\d+)===e\?"static\/chunks\/(\d+)\.([0-9a-f]+)\.js"/g)) {
  const id = Number(m[1]);
  out.set(id, `static/chunks/${m[2]}.${m[3]}.js`);
}

// tail mapping: "static/chunks/"+(({...})[e]||e)+"."+({ ... })[e]+".js"
const tailRe = /"static\/chunks\/"\+\(\(\{([^}]+)\}\)\[e\]\|\|e\)\+"\."\+\(\{([^}]+)\}\)\[e\]\+"\.js"/;
const tm = src.match(tailRe);
if(tm){
  const prefixMap = parsePairs(tm[1]);
  const hashMap = parsePairs(tm[2]);
  for(const [id,hash] of hashMap.entries()){
    const prefix = prefixMap.get(id) || String(id);
    out.set(id, `static/chunks/${prefix}.${hash}.js`);
  }
}

const sorted = [...out.entries()].sort((a,b)=>a[0]-b[0]).map(([id,path])=>({id,path}));
process.stdout.write(JSON.stringify({runtime:rtFile, count: sorted.length, chunks: sorted}, null, 2));
