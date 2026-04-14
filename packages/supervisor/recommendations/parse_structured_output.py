from __future__ import annotations

from typing import Any

REQUIRED_FIELDS = [
    'ticker',
    'thesis_type',
    'side',
    'horizon',
    'confidence',
    'why_now',
    'supporting_evidence',
    'contradicting_evidence',
    'invalidation',
    'suggested_priority',
    'notes',
]


def normalize_generated_object(obj: dict[str, Any]) -> dict[str, Any]:
    out = {key: obj.get(key) for key in REQUIRED_FIELDS}
    out['confidence'] = float(out.get('confidence') or 0.0)
    out['suggested_priority'] = int(out.get('suggested_priority') or 0)
    out['supporting_evidence'] = list(out.get('supporting_evidence') or [])
    out['contradicting_evidence'] = list(out.get('contradicting_evidence') or [])
    out['invalidation'] = dict(out.get('invalidation') or {})
    out['notes'] = str(out.get('notes') or '')
    out['why_now'] = str(out.get('why_now') or '')
    out['ticker'] = str(out.get('ticker') or '').upper()
    out['thesis_type'] = str(out.get('thesis_type') or 'signal_synthesis')
    out['side'] = str(out.get('side') or 'watch')
    out['horizon'] = str(out.get('horizon') or 'swing_5d')
    return out
