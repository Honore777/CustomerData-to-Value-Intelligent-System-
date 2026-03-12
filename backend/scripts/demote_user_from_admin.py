#!/usr/bin/env python3
"""
Demote a user from platform admin.

Usage:
  pip install psycopg2-binary
  python scripts/demote_user_from_admin.py --database-url "<DATABASE_URL>" --email "user@example.com"

This sets `is_platform_admin = FALSE` for the given email.
"""
import argparse
import os
import sys

import psycopg2


def demote(database_url: str, email: str) -> int:
    conn = psycopg2.connect(database_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users
                SET is_platform_admin = FALSE
                WHERE email = %s
                RETURNING id, email, is_platform_admin
                """,
                (email,),
            )
            row = cur.fetchone()
            if row:
                conn.commit()
                print(f"Demoted user {row[1]} (id={row[0]}) to is_platform_admin={row[2]}")
                return 0
            else:
                print("No user found with that email.")
                return 2
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Demote existing user from platform admin")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"), help="Postgres DATABASE_URL")
    parser.add_argument("--email", required=True, help="Email of the user to demote")
    args = parser.parse_args()

    if not args.database_url:
        print("Provide --database-url or set DATABASE_URL environment variable")
        sys.exit(1)

    code = demote(args.database_url, args.email)
    sys.exit(code)


if __name__ == "__main__":
    main()
