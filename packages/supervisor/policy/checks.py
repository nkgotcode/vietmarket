from __future__ import annotations

from typing import Any


def check_system_health(row: dict[str, Any]) -> dict[str, Any]:
    status = row.get('cycle_overall_status') or 'unknown'
    blocked = status not in {'healthy'}
    return {
        'check_name': 'system_health_gate',
        'passed': not blocked,
        'blocking': blocked,
        'detail': status,
    }


def check_confidence(row: dict[str, Any], *, floor: float) -> dict[str, Any]:
    confidence = float(row.get('confidence') or 0.0)
    blocked = confidence < floor
    return {
        'check_name': 'confidence_floor_gate',
        'passed': not blocked,
        'blocking': blocked,
        'detail': confidence,
    }


def check_liquidity(row: dict[str, Any], *, minimum_score: float) -> dict[str, Any]:
    liquidity_score = float(row.get('liquidity_score') or 0.0)
    blocked = liquidity_score < minimum_score
    return {
        'check_name': 'liquidity_gate',
        'passed': not blocked,
        'blocking': blocked,
        'detail': liquidity_score,
    }


def check_event_blackout(row: dict[str, Any]) -> dict[str, Any]:
    blocked = bool(row.get('has_corporate_action'))
    return {
        'check_name': 'event_blackout_gate',
        'passed': not blocked,
        'blocking': False,
        'detail': row.get('has_corporate_action'),
    }


def check_recommendation_status(row: dict[str, Any]) -> dict[str, Any]:
    status = row.get('recommendation_status') or 'draft'
    blocked = status not in {'paper_eligible', 'candidate', 'watch'}
    return {
        'check_name': 'recommendation_status_gate',
        'passed': not blocked,
        'blocking': blocked,
        'detail': status,
    }
