from __future__ import annotations

import os

import psycopg2
import psycopg2.extras


def pg_url() -> str:
    value = os.environ.get('PG_URL') or os.environ.get('DATABASE_URL')
    if not value:
        raise RuntimeError('Missing PG_URL or DATABASE_URL')
    return value


def connect():
    return psycopg2.connect(pg_url())


def dict_cursor(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)