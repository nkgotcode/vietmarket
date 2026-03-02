from __future__ import annotations

import json
import urllib.request


def render_template(tpl: str, event: dict) -> str:
    out = tpl
    for k, v in event.items():
        if isinstance(v, (str, int, float)):
            out = out.replace('{' + k + '}', str(v))
    payload = event.get('payload', {}) if isinstance(event.get('payload'), dict) else {}
    for k, v in payload.items():
        out = out.replace('{payload.' + str(k) + '}', str(v))
    return out


def send(channel: str, message: str, channels_cfg: dict):
    cfg = channels_cfg.get(channel, {})
    if channel == 'webhook':
        url = cfg.get('url')
        if not url:
            print(f'[ALERT:webhook:skip] {message}')
            return
        req = urllib.request.Request(
            url,
            data=json.dumps({'message': message}).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                _ = r.read()
            print(f'[ALERT:webhook:ok] {message}')
        except Exception as e:
            print(f'[ALERT:webhook:error] {e} :: {message}')
        return

    # default: stdout adapter (telegram/discord/email/sms placeholders)
    print(f'[ALERT:{channel}] {message}')
