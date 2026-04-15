from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any

from .dispatch import render_template, send
from .expression import eval_condition_node, eval_expr


@dataclass
class FireResult:
    rule_id: str
    fired: bool
    reason: str


def _fingerprint(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode('utf-8')).hexdigest()


def _match_scope(rule: dict, event: dict, resolved_symbols: list[str]) -> bool:
    scope = rule.get('scope', {})
    if event.get('event_type') not in (scope.get('event_types') or []):
        return False

    if resolved_symbols == ['*']:
        return True

    sym = event.get('symbol')
    if resolved_symbols:
        return sym in resolved_symbols

    # empty resolved symbol list = no symbol restriction
    return True


def process_event(event: dict, rules: list[dict], resolve_symbols_fn, store, channels_cfg: dict) -> list[FireResult]:
    out: list[FireResult] = []
    now = int(time.time())

    for rule in rules:
        rid = rule['id']
        scope_symbols = resolve_symbols_fn(rule)
        if not _match_scope(rule, event, scope_symbols):
            out.append(FireResult(rid, False, 'scope_miss'))
            continue

        key = f"{rid}:{event.get('symbol') or '*'}:{event.get('account_id') or '*'}"
        st = store.get(key)
        prev_ctx = st.get('last_event_ctx')

        ctx = {
            'event_type': event.get('event_type'),
            'source': event.get('source'),
            'symbol': event.get('symbol'),
            'tf': event.get('tf'),
            'payload': event.get('payload', {}),
        }

        matched = eval_condition_node(rule['conditions'], ctx, prev_ctx)
        mode = (rule.get('trigger') or {}).get('mode', 'on_transition')
        prev_matched = bool(st.get('prev_matched', False))
        reset_expr = (rule.get('trigger') or {}).get('reset_expr')
        armed = bool(st.get('armed', True))

        should_fire = False
        if mode == 'always':
            should_fire = matched
        elif mode == 'on_transition':
            should_fire = matched and not prev_matched
        elif mode == 'once_until_reset':
            if not armed and reset_expr and eval_expr(reset_expr, ctx, prev_ctx):
                armed = True
            should_fire = matched and armed

        # noise controls
        nc = rule.get('noise_control') or {}
        cooldown = int(nc.get('cooldown_sec', 0) or 0)
        last_fire = int(st.get('last_fire_sec', 0) or 0)
        if should_fire and cooldown > 0 and (now - last_fire) < cooldown:
            should_fire = False

        if should_fire and nc.get('dedupe_fingerprint', True):
            fp = _fingerprint(event.get('payload', {}))
            if fp == st.get('last_fingerprint'):
                should_fire = False
            else:
                st['last_fingerprint'] = fp

        if should_fire:
            tpl = rule.get('template') or {}
            title = render_template(tpl.get('title', rid), event)
            body = render_template(tpl.get('body', ''), event)
            message = f"[{rule.get('severity','medium').upper()}] {title}\n{body}"
            for ch in (rule.get('routing', {}) or {}).get('channels', []):
                send(ch, message, channels_cfg)
            st['last_fire_sec'] = now
            if mode == 'once_until_reset':
                armed = False
            out.append(FireResult(rid, True, 'fired'))
        else:
            out.append(FireResult(rid, False, 'no_fire'))

        st['armed'] = armed
        st['prev_matched'] = bool(matched)
        st['last_event_ctx'] = ctx
        store.set(key, st)

    return out
