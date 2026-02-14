#!/usr/bin/env node
/**
 * Best-effort static tracer for Simplize minified bundles.
 * Goal: find call-sites that invoke module 74427's historicalPrices and print param-object keys.
 *
 * Usage:
 *   node trace_ohlcv_params.js /tmp/simplize_crawl/chunks
 */
const fs = require('fs');
const path = require('path');
const acorn = require('acorn');
const walk = require('acorn-walk');

const root = process.argv[2];
if (!root) {
  console.error('Usage: node trace_ohlcv_params.js <chunks_dir>');
  process.exit(2);
}

function listJsFiles(dir) {
  const out = [];
  const stack = [dir];
  while (stack.length) {
    const d = stack.pop();
    let ents;
    try {
      ents = fs.readdirSync(d, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const ent of ents) {
      const p = path.join(d, ent.name);
      if (ent.isDirectory()) stack.push(p);
      else if (ent.isFile() && ent.name.endsWith('.js')) out.push(p);
    }
  }
  return out;
}

function isRequire74427(node) {
  // webpack-style require: <ident>(74427) where ident varies (i, t, n, e, ...)
  return (
    node &&
    node.type === 'CallExpression' &&
    node.callee &&
    node.callee.type === 'Identifier' &&
    node.arguments &&
    node.arguments.length === 1 &&
    node.arguments[0].type === 'Literal' &&
    node.arguments[0].value === 74427
  );
}

function memberPropName(mem) {
  if (!mem || mem.type !== 'MemberExpression') return null;
  if (mem.computed) {
    return mem.property && mem.property.type === 'Literal' ? String(mem.property.value) : null;
  }
  return mem.property && mem.property.type === 'Identifier' ? mem.property.name : null;
}

function isHistoricalPricesCallee(callee, importedNamesSet) {
  // We’re looking for something like: X.i.historicalPrices(...) or X.i["historicalPrices"](...)
  if (!callee || callee.type !== 'MemberExpression') return false;

  const p0 = memberPropName(callee);
  if (p0 !== 'historicalPrices') return false;

  const obj = callee.object;
  if (!obj || obj.type !== 'MemberExpression') return false;
  const p1 = memberPropName(obj);
  if (p1 !== 'i') return false;

  const base = obj.object;
  if (!base) return false;

  // base might be Identifier (assigned from require) OR directly the require call t(74427)
  if (base.type === 'Identifier') return importedNamesSet.has(base.name);
  if (isRequire74427(base)) return true;

  return false;
}

function prettyNodeSnippet(src, node, pad = 120) {
  if (!node || typeof node.start !== 'number' || typeof node.end !== 'number') return '';
  const s = Math.max(0, node.start - pad);
  const e = Math.min(src.length, node.end + pad);
  return src.slice(s, e).replace(/\s+/g, ' ').trim();
}

function objectKeysFromExpression(expr) {
  if (!expr) return null;
  if (expr.type === 'ObjectExpression') {
    const keys = [];
    for (const prop of expr.properties || []) {
      if (prop.type !== 'Property') continue;
      if (prop.key.type === 'Identifier') keys.push(prop.key.name);
      else if (prop.key.type === 'Literal') keys.push(String(prop.key.value));
      else keys.push('<nonliteral>');
    }
    return keys;
  }
  return null;
}

function traceFile(filePath) {
  const src = fs.readFileSync(filePath, 'utf8');
  // cheap prefilter to avoid parsing every huge file
  if (!(src.includes('74427') && src.includes('historicalPrices'))) return [];

  let ast;
  try {
    ast = acorn.parse(src, {
      ecmaVersion: 'latest',
      sourceType: 'script',
      allowHashBang: true,
      allowReturnOutsideFunction: true,
    });
  } catch (e) {
    return [{ filePath, error: `parse_error: ${e.message}` }];
  }

  const importedNames = new Set();

  // pass 1: collect identifiers assigned from i(74427)
  walk.simple(ast, {
    VariableDeclarator(node) {
      if (node.id && node.id.type === 'Identifier' && isRequire74427(node.init)) {
        importedNames.add(node.id.name);
      }
    },
    AssignmentExpression(node) {
      // X = i(74427)
      if (node.left && node.left.type === 'Identifier' && isRequire74427(node.right)) {
        importedNames.add(node.left.name);
      }
    },
  });

  if (importedNames.size === 0) return [];

  const hits = [];

  // pass 2: find call expressions
  walk.ancestor(ast, {
    CallExpression(node, ancestors) {
      if (!isHistoricalPricesCallee(node.callee, importedNames)) return;

      const arg0 = node.arguments && node.arguments[0];
      let keys = objectKeysFromExpression(arg0);
      let resolvedFrom = null;

      if (!keys && arg0 && arg0.type === 'Identifier') {
        // best-effort: resolve within the nearest function/block scope by scanning ancestors backwards
        const name = arg0.name;
        for (let ai = ancestors.length - 1; ai >= 0; ai--) {
          const anc = ancestors[ai];
          if (!anc || !anc.body) continue;
          const body = Array.isArray(anc.body) ? anc.body : (anc.body.body && Array.isArray(anc.body.body) ? anc.body.body : null);
          if (!body) continue;
          // find statement containing the call, then scan earlier statements
          const callStmtIdx = body.findIndex(st => st && st.start <= node.start && st.end >= node.end);
          const scanUntil = callStmtIdx >= 0 ? callStmtIdx : body.length;
          for (let si = scanUntil - 1; si >= 0; si--) {
            const st = body[si];
            if (!st) continue;
            // var name = { ... }
            if (st.type === 'VariableDeclaration') {
              for (const decl of st.declarations || []) {
                if (decl.id && decl.id.type === 'Identifier' && decl.id.name === name) {
                  keys = objectKeysFromExpression(decl.init);
                  if (keys) {
                    resolvedFrom = 'var_decl';
                    break;
                  }
                }
              }
              if (keys) break;
            }
            // name = { ... }
            if (st.type === 'ExpressionStatement' && st.expression && st.expression.type === 'AssignmentExpression') {
              const asn = st.expression;
              if (asn.left && asn.left.type === 'Identifier' && asn.left.name === name) {
                keys = objectKeysFromExpression(asn.right);
                if (keys) {
                  resolvedFrom = 'assignment';
                  break;
                }
              }
            }
          }
          if (keys) break;
        }
      }

      hits.push({
        filePath,
        importedNames: Array.from(importedNames),
        keys,
        resolvedFrom,
        snippet: prettyNodeSnippet(src, node),
      });
    },
  });

  return hits;
}

const files = listJsFiles(root);
const results = [];
for (const f of files) {
  const r = traceFile(f);
  if (r && r.length) results.push(...r);
}

process.stdout.write(JSON.stringify({ root, files: files.length, results }, null, 2));
