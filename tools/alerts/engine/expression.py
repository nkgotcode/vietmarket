from __future__ import annotations

import math
from typing import Any



class DotDict(dict):
    __getattr__ = dict.get


def _dot(v):
    if isinstance(v, dict):
        return DotDict({k: _dot(x) for k, x in v.items()})
    if isinstance(v, list):
        return [_dot(x) for x in v]
    return v

def _get(path: str, ctx: dict) -> Any:
    cur: Any = ctx
    for p in path.split('.'):
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return None
    return cur


def _num(v: Any) -> float | None:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def eval_expr(expr: str, ctx: dict, prev_ctx: dict | None = None) -> bool:
    expr = expr.strip()

    # Special operators: "a crosses_above b" / "a crosses_below b"
    if ' crosses_above ' in expr:
        l, r = expr.split(' crosses_above ', 1)
        c_l, c_r = _num(_get(l.strip(), ctx)), _num(_get(r.strip(), ctx))
        p_l = _num(_get(l.strip(), prev_ctx or {}))
        p_r = _num(_get(r.strip(), prev_ctx or {}))
        return all(v is not None for v in [c_l, c_r, p_l, p_r]) and p_l <= p_r and c_l > c_r

    if ' crosses_below ' in expr:
        l, r = expr.split(' crosses_below ', 1)
        c_l, c_r = _num(_get(l.strip(), ctx)), _num(_get(r.strip(), ctx))
        p_l = _num(_get(l.strip(), prev_ctx or {}))
        p_r = _num(_get(r.strip(), prev_ctx or {}))
        return all(v is not None for v in [c_l, c_r, p_l, p_r]) and p_l >= p_r and c_l < c_r

    # Safe-eval for regular expressions (subset)
    safe_locals = {
        'payload': _dot(ctx.get('payload', {})),
        'symbol': ctx.get('symbol'),
        'tf': ctx.get('tf'),
        'event_type': ctx.get('event_type'),
        'source': ctx.get('source'),
        'math': math,
    }
    try:
        return bool(eval(expr, {'__builtins__': {}}, safe_locals))
    except Exception:
        return False


def eval_condition_node(node: dict, ctx: dict, prev_ctx: dict | None = None) -> bool:
    if 'expr' in node:
        return eval_expr(node['expr'], ctx, prev_ctx)

    op = node.get('op')
    args = node.get('args', [])
    if op == 'AND':
        return all(eval_condition_node(a, ctx, prev_ctx) for a in args)
    if op == 'OR':
        return any(eval_condition_node(a, ctx, prev_ctx) for a in args)
    if op == 'NOT':
        return not eval_condition_node(args[0], ctx, prev_ctx) if args else False
    return False
