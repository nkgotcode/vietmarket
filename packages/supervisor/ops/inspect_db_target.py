#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import psycopg2.extras

from packages.supervisor.common.db import connect, pg_url


def _dsn_summary() -> dict:
    parsed = urlparse(pg_url())
    return {
        'scheme': parsed.scheme,
        'host': parsed.hostname,
        'port': parsed.port,
        'database': parsed.path.lstrip('/') or None,
        'user': parsed.username,
    }


def inspect_db_target() -> dict:
    with connect() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                '''
                SELECT current_database() AS database_name,
                       current_user AS current_user,
                       current_setting('transaction_read_only') AS transaction_read_only,
                       pg_is_in_recovery() AS in_recovery,
                       inet_server_addr()::text AS server_addr,
                       inet_server_port() AS server_port,
                       version() AS postgres_version,
                       now() AS observed_at
                '''
            )
            row = dict(cur.fetchone())

    read_only = str(row.get('transaction_read_only') or '').lower() == 'on'
    in_recovery = bool(row.get('in_recovery'))
    return {
        'ok': True,
        'dsn': _dsn_summary(),
        'database_name': row.get('database_name'),
        'current_user': row.get('current_user'),
        'transaction_read_only': row.get('transaction_read_only'),
        'in_recovery': in_recovery,
        'server_addr': row.get('server_addr'),
        'server_port': row.get('server_port'),
        'postgres_version': row.get('postgres_version'),
        'observed_at': row.get('observed_at'),
        'writable_primary': not read_only and not in_recovery,
        'recommended_next_step': 'safe_to_run_live_write_verification' if (not read_only and not in_recovery) else 'point PG_URL or DATABASE_URL at writable primary before live migrations or supervisor write-path verification',
        'environment_variable_source': 'PG_URL' if os.environ.get('PG_URL') else 'DATABASE_URL',
    }


if __name__ == '__main__':
    print(json.dumps(inspect_db_target(), default=str, ensure_ascii=False))
