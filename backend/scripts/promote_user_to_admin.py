#!/usr/bin/env python3
"""
promote_user_to_admin.py

Simple helper to promote an existing user row to platform admin.

Usage:
  pip install psycopg2-binary
  python scripts/promote_user_to_admin.py --database-url "<DATABASE_URL>" --email "you@example.com"

It runs a single UPDATE on the `users` table setting `is_platform_admin = true` for the given email.
Make sure you've already run migrations and that the user exists (create account via frontend or insert via SQL).
"""
import argparse
import os
import sys

import psycopg2


def promote(database_url: str, email: str) -> int:
    conn = psycopg2.connect(database_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users
                SET is_platform_admin = TRUE
                WHERE email = %s
                RETURNING id, email, is_platform_admin
                """,
                (email,),
            )
            row = cur.fetchone()
            if row:
                conn.commit()
                print(f"Promoted user {row[1]} (id={row[0]}) to is_platform_admin={row[2]}")
                return 0
            else:
                print("No user found with that email. Create the user first (via frontend or SQL), then run this.")
                return 2
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Promote existing user to platform admin")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"), help="Postgres DATABASE_URL")
    parser.add_argument("--email", required=True, help="Email of the user to promote")
    args = parser.parse_args()

    if not args.database_url:
        print("Provide --database-url or set DATABASE_URL environment variable")
        sys.exit(1)

    code = promote(args.database_url, args.email)
    sys.exit(code)


if __name__ == "__main__":
    main()
