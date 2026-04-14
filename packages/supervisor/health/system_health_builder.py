from __future__ import annotations

import json

from packages.supervisor.common.db import connect, dict_cursor
from packages.supervisor.common.enums import FRESHNESS_STALE, FRESHNESS_UNKNOWN, SEVERITY_WARNING
from packages.supervisor.common.ids import new_issue_id, new_snapshot_id
from packages.supervisor.common.time import utc_now

BLOCKING_RULES = {
    ('candles', '15m'): ('critical', True, 'candles_15m_unhealthy', '15m candles are stale or unknown'),
    ('symbols', None): ('critical', True, 'symbols_unhealthy', 'symbols dataset is stale or unknown'),
}
WARNING_RULES = {
    ('candles', '1h'): ('warning', False, 'candles_1h_lagging', '1h candles are lagging'),
    ('candles', '1d'): ('warning', False, 'candles_1d_lagging', '1d candles are lagging'),
    ('fi_latest', None): ('warning', False, 'fi_latest_lagging', 'financial latest data is lagging'),
    ('corporate_actions', None): ('warning', False, 'corporate_actions_lagging', 'corporate actions data is lagging'),
    ('articles', None): ('warning', False, 'articles_lagging', 'articles are lagging'),
    ('market_stats', None): ('warning', False, 'market_stats_lagging', 'market stats are lagging'),
}


def build_system_health() -> dict:
    now = utc_now()
    snapshot_id = new_snapshot_id()
    issues: list[dict] = []
    with connect() as conn:
        with dict_cursor(conn) as cur:
            cur.execute('SELECT dataset_name, tf, freshness_status FROM dataset_freshness ORDER BY dataset_name, tf NULLS FIRST')
            freshness_rows = cur.fetchall()
            for row in freshness_rows:
                key = (row['dataset_name'], row['tf'])
                status = row['freshness_status']
                if key in BLOCKING_RULES and status in {FRESHNESS_STALE, FRESHNESS_UNKNOWN}:
                    sev, blocking, code, message = BLOCKING_RULES[key]
                    issues.append({'issue_id': new_issue_id(), 'severity': sev, 'scope_type': 'dataset', 'scope_key': f"{row['dataset_name']}:{row['tf'] or 'all'}", 'issue_code': code, 'issue_message': message, 'blocking': blocking})
                elif key in WARNING_RULES and status in {FRESHNESS_STALE, FRESHNESS_UNKNOWN, 'lagging'}:
                    sev, blocking, code, message = WARNING_RULES[key]
                    issues.append({'issue_id': new_issue_id(), 'severity': sev, 'scope_type': 'dataset', 'scope_key': f"{row['dataset_name']}:{row['tf'] or 'all'}", 'issue_code': code, 'issue_message': message, 'blocking': blocking})

            overall = 'healthy'
            if any(i['blocking'] for i in issues):
                overall = 'blocked'
            elif issues:
                overall = 'degraded'

            cur.execute(
                '''INSERT INTO system_health_snapshots (snapshot_id, cycle_id, overall_status, data_plane_status, freshness_status, notes_json, created_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)''',
                (snapshot_id, None, overall, overall, overall, json.dumps({'issue_count': len(issues)}), now)
            )
            for issue in issues:
                cur.execute(
                    '''INSERT INTO system_health_issues (issue_id, snapshot_id, severity, scope_type, scope_key, issue_code, issue_message, blocking, created_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
                    (issue['issue_id'], snapshot_id, issue['severity'], issue['scope_type'], issue['scope_key'], issue['issue_code'], issue['issue_message'], issue['blocking'], now)
                )
    return {
        'ok': True,
        'snapshot_id': snapshot_id,
        'overall_status': overall,
        'blocking_issue_count': sum(1 for i in issues if i['blocking']),
        'warning_count': sum(1 for i in issues if i['severity'] == SEVERITY_WARNING),
        'created_at': now.isoformat(timespec='seconds'),
    }