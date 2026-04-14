from __future__ import annotations

import json


def format_daily_brief(brief: dict) -> str:
    return f"{brief.get('title','Daily brief')}\n\n{brief.get('summary_text','')}\n\n{json.dumps(brief.get('brief_json') or {}, ensure_ascii=False, indent=2)}"


def format_intraday_alerts(alerts: list[dict]) -> str:
    if not alerts:
        return 'No active alerts.'
    return '\n'.join(f"- {a.get('severity','info').upper()}: {a.get('message','')}" for a in alerts)
