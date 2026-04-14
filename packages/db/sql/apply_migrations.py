#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path

import psycopg2


def pg_url() -> str:
    value = os.environ.get('PG_URL') or os.environ.get('DATABASE_URL')
    if not value:
        raise RuntimeError('Missing PG_URL or DATABASE_URL')
    return value


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def migration_dir() -> Path:
    return repo_root() / 'packages' / 'db' / 'migrations'


def ensure_schema_table(cur) -> None:
    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS schema_migrations (
          name TEXT PRIMARY KEY,
          applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        '''
    )


def main() -> int:
    migrations = sorted(migration_dir().glob('*.sql'))
    with psycopg2.connect(pg_url()) as conn:
        with conn.cursor() as cur:
            ensure_schema_table(cur)
            cur.execute('SELECT name FROM schema_migrations')
            applied = {row[0] for row in cur.fetchall()}
            applied_now: list[str] = []
            for path in migrations:
                if path.name in applied:
                    continue
                cur.execute(path.read_text())
                cur.execute('INSERT INTO schema_migrations(name) VALUES (%s)', (path.name,))
                applied_now.append(path.name)
    print({'ok': True, 'applied': applied_now, 'count': len(applied_now)})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())