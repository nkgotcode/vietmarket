from __future__ import annotations

import json
import os
from urllib import error, request

TELEGRAM_API = 'https://api.telegram.org'


def telegram_target() -> str | None:
    return os.environ.get('TELEGRAM_CHAT_ID') or os.environ.get('TELEGRAM_TARGET_CHAT_ID')


def prepare_telegram_message(text: str) -> dict:
    return {'channel': 'telegram', 'chat_id': telegram_target(), 'text': text}


def send_telegram_message(message: dict) -> dict:
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = message.get('chat_id') or telegram_target()
    if not token or not chat_id:
        return {
            'ok': False,
            'delivery_status': 'dry_run',
            'reason': 'missing_telegram_credentials',
            'channel': 'telegram',
            'chat_id': chat_id,
            'text': message.get('text'),
        }

    body = json.dumps({
        'chat_id': chat_id,
        'text': message.get('text', ''),
        'disable_web_page_preview': True,
    }).encode('utf-8')
    req = request.Request(
        f'{TELEGRAM_API}/bot{token}/sendMessage',
        data=body,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode('utf-8'))
            return {
                'ok': bool(payload.get('ok')),
                'delivery_status': 'sent' if payload.get('ok') else 'failed',
                'channel': 'telegram',
                'chat_id': chat_id,
                'response': payload,
            }
    except error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='replace')
        return {
            'ok': False,
            'delivery_status': 'failed',
            'channel': 'telegram',
            'chat_id': chat_id,
            'error': f'http_{exc.code}',
            'detail': detail,
        }
    except Exception as exc:  # pragma: no cover - defensive network path
        return {
            'ok': False,
            'delivery_status': 'failed',
            'channel': 'telegram',
            'chat_id': chat_id,
            'error': type(exc).__name__,
            'detail': str(exc),
        }
