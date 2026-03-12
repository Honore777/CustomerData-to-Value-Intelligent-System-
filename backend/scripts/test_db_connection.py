#!/usr/bin/env python3
"""
Simple tester to attempt a DB connection using `DATABASE_URL` from env.

Usage:
  pip install psycopg2-binary
  python scripts/test_db_connection.py

It prints the DATABASE_URL (with password redacted) and the full exception trace if connection fails.
"""
import os
import traceback
from urllib.parse import urlparse

import psycopg2


def redact(url: str) -> str:
    try:
        p = urlparse(url)
        pwd = p.password
        red = url.replace(p.password, '***REDACTED***') if pwd else url
        return red
    except Exception:
        return 'invalid-url'


def main():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print('No DATABASE_URL set in environment. Load your .env or export DATABASE_URL first.')
        return

    print('Using DATABASE_URL:', redact(database_url))
    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute('SELECT 1')
        print('Connection OK, SELECT 1 returned:', cur.fetchone())
        cur.close()
        conn.close()
    except Exception as e:
        print('Connection failed; printing full traceback:')
        traceback.print_exc()


if __name__ == '__main__':
    main()
