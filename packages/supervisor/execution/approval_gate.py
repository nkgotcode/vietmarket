from __future__ import annotations

from packages.supervisor.common.db import connect


def evaluate_approval_requirements(*, recommendation_id: str | None, paper_order_id: str | None) -> dict:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT overall_status FROM system_health_snapshots ORDER BY created_at DESC LIMIT 1')
            health = cur.fetchone()
            overall_status = health[0] if health else 'unknown'
            cur.execute('SELECT count(*) FROM portfolio_snapshots')
            portfolio_ready = (cur.fetchone() or [0])[0] > 0
            allowed = overall_status == 'healthy' and portfolio_ready
            return {
                'required': True,
                'allowed_for_staging': allowed,
                'overall_status': overall_status,
                'portfolio_ready': portfolio_ready,
                'recommendation_id': recommendation_id,
                'paper_order_id': paper_order_id,
            }
