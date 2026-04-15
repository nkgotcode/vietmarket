from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path


def render_template(tpl: str, event: dict) -> str:
    out = tpl
    for k, v in event.items():
        if isinstance(v, (str, int, float)):
            out = out.replace('{' + k + '}', str(v))
    payload = event.get('payload', {}) if isinstance(event.get('payload'), dict) else {}
    for k, v in payload.items():
        out = out.replace('{payload.' + str(k) + '}', str(v))
    return out


def _append_dead_letter(channel: str, message: str, error: str, cfg: dict):
    p = Path(cfg.get('dead_letter', 'runtime/alerts/dead_letters.jsonl'))
    p.parent.mkdir(parents=True, exist_ok=True)
    row = {'ts': int(time.time()), 'channel': channel, 'message': message, 'error': error}
    with p.open('a', encoding='utf-8') as f:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')


def _post_json(url: str, body: dict, timeout: int = 10):
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def send(channel: str, message: str, channels_cfg: dict):
    cfg = channels_cfg.get(channel, {})

    try:
        if channel == 'telegram':
            token = cfg.get('bot_token') or os.getenv('ALERT_TELEGRAM_BOT_TOKEN', '')
            chat_id = str(cfg.get('chat_id') or os.getenv('ALERT_TELEGRAM_CHAT_ID', ''))
            if not token or not chat_id:
                print(f'[ALERT:telegram:skip] missing token/chat_id :: {message}')
                return
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            _post_json(url, {'chat_id': chat_id, 'text': message, 'disable_web_page_preview': True})
            print(f'[ALERT:telegram:ok] {message}')
            return

        if channel == 'discord':
            webhook = cfg.get('webhook_url') or os.getenv('ALERT_DISCORD_WEBHOOK_URL', '')
            if not webhook:
                print(f'[ALERT:discord:skip] missing webhook_url :: {message}')
                return
            _post_json(webhook, {'content': message})
            print(f'[ALERT:discord:ok] {message}')
            return

        if channel == 'webhook':
            url = cfg.get('url') or os.getenv('ALERT_WEBHOOK_URL', '')
            if not url:
                print(f'[ALERT:webhook:skip] {message}')
                return
            _post_json(url, {'message': message})
            print(f'[ALERT:webhook:ok] {message}')
            return

        # placeholders
        print(f'[ALERT:{channel}] {message}')
    except Exception as e:
        print(f'[ALERT:{channel}:error] {e} :: {message}')
        _append_dead_letter(channel, message, str(e), cfg)
