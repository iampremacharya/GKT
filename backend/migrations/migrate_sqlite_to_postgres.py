"""Migrate the existing Find Your 7 Twins SQLite database into PostgreSQL.

Usage:
  DATABASE_URL='postgresql://...' python migrations/migrate_sqlite_to_postgres.py \
      --sqlite /path/to/twins.db

The script preserves user IDs, swipes, and reset-token rows so existing
relationships continue to work. Uploaded images must be copied separately to
STORAGE_DIR/uploads using the original filenames.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))



def normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sqlite", required=True, help="Path to the existing twins.db")
    args = parser.parse_args()

    sqlite_path = Path(args.sqlite).resolve()
    target_url = normalize_database_url(os.getenv("DATABASE_URL", "").strip())
    if not target_url or target_url.startswith("sqlite:"):
        raise SystemExit("DATABASE_URL must point to the target PostgreSQL database.")
    if not sqlite_path.is_file():
        raise SystemExit(f"SQLite database not found: {sqlite_path}")

    # database.py reads DATABASE_URL when it is imported.
    os.environ["DATABASE_URL"] = target_url
    from database import initialize_database  # noqa: PLC0415
    initialize_database()
    engine = create_engine(target_url, pool_pre_ping=True)

    src = sqlite3.connect(sqlite_path)
    src.row_factory = sqlite3.Row

    with engine.begin() as dst:
        users = src.execute("SELECT * FROM users ORDER BY id").fetchall()
        swipes = src.execute("SELECT * FROM swipes ORDER BY id").fetchall()
        resets = src.execute("SELECT * FROM password_reset_tokens ORDER BY id").fetchall()

        for row in users:
            dst.execute(
                text(
                    """
                    INSERT INTO users
                    (id,username,email,password_hash,name,country,photo_path,embedding,discoverable,created_at)
                    VALUES (:id,:username,:email,:password_hash,:name,:country,:photo_path,:embedding,:discoverable,:created_at)
                    ON CONFLICT (id) DO UPDATE SET
                        username=EXCLUDED.username,email=EXCLUDED.email,password_hash=EXCLUDED.password_hash,
                        name=EXCLUDED.name,country=EXCLUDED.country,photo_path=EXCLUDED.photo_path,
                        embedding=EXCLUDED.embedding,discoverable=EXCLUDED.discoverable,created_at=EXCLUDED.created_at
                    """
                ),
                dict(row),
            )

        for row in swipes:
            dst.execute(
                text(
                    """
                    INSERT INTO swipes (id,user_id,target_user_id,direction,created_at)
                    VALUES (:id,:user_id,:target_user_id,:direction,:created_at)
                    ON CONFLICT (user_id,target_user_id) DO UPDATE SET
                        direction=EXCLUDED.direction,created_at=EXCLUDED.created_at
                    """
                ),
                dict(row),
            )

        for row in resets:
            dst.execute(
                text(
                    """
                    INSERT INTO password_reset_tokens
                    (id,user_id,token_hash,expires_at,used,created_at)
                    VALUES (:id,:user_id,:token_hash,:expires_at,:used,:created_at)
                    ON CONFLICT (token_hash) DO UPDATE SET
                        user_id=EXCLUDED.user_id,expires_at=EXCLUDED.expires_at,
                        used=EXCLUDED.used,created_at=EXCLUDED.created_at
                    """
                ),
                dict(row),
            )

        # Keep generated IDs ahead of the imported values.
        for table in ("users", "swipes", "password_reset_tokens"):
            dst.execute(
                text(
                    f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM {table}), 1), true)"
                )
            )

    src.close()
    print(f"Migrated {len(users)} users, {len(swipes)} swipes and {len(resets)} reset-token rows.")
    print("Copy the corresponding uploads directory to STORAGE_DIR/uploads before serving traffic.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
