from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine, RowMapping

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

if not DATABASE_URL:
    DATABASE_URL = f"sqlite:///{DATA_DIR / 'twins.db'}"

# Render/Postgres URLs can occasionally use postgres://; SQLAlchemy expects postgresql://.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL[len("postgres://") :]
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL[len("postgresql://") :]

IS_SQLITE = DATABASE_URL.startswith("sqlite:")

engine_kwargs: dict[str, Any] = {
    "pool_pre_ping": True,
}

if IS_SQLITE:
    engine_kwargs.update(
        connect_args={"check_same_thread": False, "timeout": 15},
    )
else:
    engine_kwargs.update(pool_size=int(os.getenv("DB_POOL_SIZE", "5")), max_overflow=2)

engine: Engine = create_engine(DATABASE_URL, **engine_kwargs)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row(result) -> RowMapping | None:
    row = result.mappings().first()
    return row


def _rows(result) -> list[RowMapping]:
    return list(result.mappings().all())


def get_connection() -> Connection:
    """Compatibility helper for code that needs a SQLAlchemy connection."""
    return engine.connect()


def _initialize_sqlite_compat() -> None:
    if not IS_SQLITE:
        return
    with engine.begin() as conn:
        # The production schema is portable, but SQLite needs INTEGER PRIMARY KEY
        # rather than GENERATED AS IDENTITY. Create/upgrade it explicitly.
        tables = {
            r[0]
            for r in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).all()
        }
        if "users" not in tables:
            conn.execute(
                text(
                    """
                    CREATE TABLE users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT,
                        email TEXT,
                        password_hash TEXT,
                        name TEXT NOT NULL,
                        country TEXT NOT NULL,
                        photo_path TEXT NOT NULL,
                        embedding TEXT NOT NULL,
                        discoverable INTEGER NOT NULL DEFAULT 1,
                        created_at TEXT NOT NULL
                    )
                    """
                )
            )
        if "swipes" not in tables:
            conn.execute(
                text(
                    """
                    CREATE TABLE swipes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        target_user_id INTEGER NOT NULL,
                        direction TEXT NOT NULL CHECK(direction IN ('like', 'pass')),
                        created_at TEXT NOT NULL,
                        UNIQUE(user_id, target_user_id),
                        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                        FOREIGN KEY(target_user_id) REFERENCES users(id) ON DELETE CASCADE
                    )
                    """
                )
            )
        if "password_reset_tokens" not in tables:
            conn.execute(
                text(
                    """
                    CREATE TABLE password_reset_tokens (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        token_hash TEXT NOT NULL UNIQUE,
                        expires_at TEXT NOT NULL,
                        used INTEGER NOT NULL DEFAULT 0,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                    )
                    """
                )
            )

        columns = {r[1] for r in conn.execute(text("PRAGMA table_info(users)")).all()}
        for col, ddl in (
            ("username", "ALTER TABLE users ADD COLUMN username TEXT"),
            ("email", "ALTER TABLE users ADD COLUMN email TEXT"),
            ("password_hash", "ALTER TABLE users ADD COLUMN password_hash TEXT"),
        ):
            if col not in columns:
                conn.execute(text(ddl))

        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_lower "
                "ON users(lower(username)) WHERE username IS NOT NULL"
            )
        )
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_lower "
                "ON users(lower(email)) WHERE email IS NOT NULL"
            )
        )
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_swipes_user ON swipes(user_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_swipes_target ON swipes(target_user_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_password_reset_user ON password_reset_tokens(user_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_password_reset_token ON password_reset_tokens(token_hash)"))


def initialize_database() -> None:
    if IS_SQLITE:
        _initialize_sqlite_compat()
        return

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    username TEXT,
                    email TEXT,
                    password_hash TEXT,
                    name TEXT NOT NULL,
                    country TEXT NOT NULL,
                    photo_path TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    discoverable INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS swipes (
                    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    target_user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    direction TEXT NOT NULL CHECK(direction IN ('like', 'pass')),
                    created_at TEXT NOT NULL,
                    UNIQUE(user_id, target_user_id)
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS password_reset_tokens (
                    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    token_hash TEXT NOT NULL UNIQUE,
                    expires_at TEXT NOT NULL,
                    used INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_lower "
                "ON users(lower(username)) WHERE username IS NOT NULL"
            )
        )
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_lower "
                "ON users(lower(email)) WHERE email IS NOT NULL"
            )
        )
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_swipes_user ON swipes(user_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_swipes_target ON swipes(target_user_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_password_reset_user ON password_reset_tokens(user_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_password_reset_token ON password_reset_tokens(token_hash)"))


def create_user(username, email, password_hash, name, country, photo_path, embedding, discoverable=True):
    with engine.begin() as conn:
        result = conn.execute(
            text(
                """
                INSERT INTO users
                    (username,email,password_hash,name,country,photo_path,embedding,discoverable,created_at)
                VALUES (:username,:email,:password_hash,:name,:country,:photo_path,:embedding,:discoverable,:created_at)
                RETURNING id
                """
            ),
            {
                "username": username,
                "email": email,
                "password_hash": password_hash,
                "name": name,
                "country": country,
                "photo_path": photo_path,
                "embedding": json.dumps(list(embedding)),
                "discoverable": 1 if discoverable else 0,
                "created_at": utc_now_iso(),
            },
        )
        return result.scalar_one()


def get_user(user_id):
    with engine.connect() as conn:
        return _row(conn.execute(text("SELECT * FROM users WHERE id = :id"), {"id": user_id}))


def get_user_by_username(username):
    with engine.connect() as conn:
        return _row(conn.execute(text("SELECT * FROM users WHERE lower(username)=lower(:username)"), {"username": username}))


def get_user_by_email(email):
    with engine.connect() as conn:
        return _row(conn.execute(text("SELECT * FROM users WHERE lower(email)=lower(:email)"), {"email": email}))


def get_user_by_username_or_email(identifier):
    with engine.connect() as conn:
        return _row(
            conn.execute(
                text(
                    """
                    SELECT * FROM users
                    WHERE lower(username)=lower(:identifier)
                       OR lower(email)=lower(:identifier)
                    LIMIT 1
                    """
                ),
                {"identifier": identifier},
            )
        )


def get_discoverable_users(exclude_user_id):
    with engine.connect() as conn:
        return _rows(
            conn.execute(
                text(
                    """
                    SELECT u.* FROM users u
                    WHERE u.discoverable=1
                      AND u.id != :id
                      AND NOT EXISTS (
                        SELECT 1 FROM swipes s
                        WHERE s.user_id=:id AND s.target_user_id=u.id
                      )
                    ORDER BY u.id DESC
                    """
                ),
                {"id": exclude_user_id},
            )
        )


def get_all_users():
    with engine.connect() as conn:
        return _rows(conn.execute(text("SELECT * FROM users ORDER BY id DESC")))


def embedding_from_row(row):
    return json.loads(row["embedding"])


def update_user_profile(user_id, name, country, discoverable, photo_path=None, embedding=None):
    with engine.begin() as conn:
        if photo_path is not None and embedding is not None:
            conn.execute(
                text(
                    """
                    UPDATE users SET name=:name,country=:country,discoverable=:discoverable,
                    photo_path=:photo_path,embedding=:embedding WHERE id=:id
                    """
                ),
                {
                    "name": name,
                    "country": country,
                    "discoverable": 1 if discoverable else 0,
                    "photo_path": photo_path,
                    "embedding": json.dumps(list(embedding)),
                    "id": user_id,
                },
            )
        else:
            conn.execute(
                text(
                    "UPDATE users SET name=:name,country=:country,discoverable=:discoverable WHERE id=:id"
                ),
                {"name": name, "country": country, "discoverable": 1 if discoverable else 0, "id": user_id},
            )


def update_user_email(user_id, email):
    with engine.begin() as conn:
        conn.execute(text("UPDATE users SET email=:email WHERE id=:id"), {"email": email, "id": user_id})


def update_password(user_id, password_hash):
    with engine.begin() as conn:
        result = conn.execute(text("UPDATE users SET password_hash=:password_hash WHERE id=:id"), {"password_hash": password_hash, "id": user_id})
        if result.rowcount != 1:
            raise RuntimeError(f"Password update affected {result.rowcount} rows for user_id={user_id}.")


def delete_user(user_id):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM users WHERE id=:id"), {"id": user_id})


def create_or_update_swipe(user_id, target_user_id, direction):
    with engine.begin() as conn:
        if IS_SQLITE:
            conn.execute(
                text(
                    """
                    INSERT INTO swipes(user_id,target_user_id,direction,created_at)
                    VALUES (:user_id,:target_user_id,:direction,:created_at)
                    ON CONFLICT(user_id,target_user_id) DO UPDATE SET
                        direction=excluded.direction,created_at=excluded.created_at
                    """
                ),
                {"user_id": user_id, "target_user_id": target_user_id, "direction": direction, "created_at": utc_now_iso()},
            )
        else:
            conn.execute(
                text(
                    """
                    INSERT INTO swipes(user_id,target_user_id,direction,created_at)
                    VALUES (:user_id,:target_user_id,:direction,:created_at)
                    ON CONFLICT(user_id,target_user_id) DO UPDATE SET
                        direction=EXCLUDED.direction,created_at=EXCLUDED.created_at
                    """
                ),
                {"user_id": user_id, "target_user_id": target_user_id, "direction": direction, "created_at": utc_now_iso()},
            )


def create_swipe_once(user_id, target_user_id, direction):
    with engine.begin() as conn:
        result = conn.execute(
            text(
                """
                INSERT INTO swipes(user_id,target_user_id,direction,created_at)
                VALUES (:user_id,:target_user_id,:direction,:created_at)
                ON CONFLICT(user_id,target_user_id) DO NOTHING
                """
            ),
            {"user_id": user_id, "target_user_id": target_user_id, "direction": direction, "created_at": utc_now_iso()},
        )
        return result.rowcount == 1


def get_swipe(user_id, target_user_id):
    with engine.connect() as conn:
        return _row(
            conn.execute(
                text("SELECT * FROM swipes WHERE user_id=:user_id AND target_user_id=:target_user_id"),
                {"user_id": user_id, "target_user_id": target_user_id},
            )
        )


def get_user_swipes(user_id):
    with engine.connect() as conn:
        return _rows(conn.execute(text("SELECT * FROM swipes WHERE user_id=:id ORDER BY created_at DESC"), {"id": user_id}))


def is_mutual_match(user_id, target_user_id):
    with engine.connect() as conn:
        result = conn.execute(
            text(
                """
                SELECT 1 FROM swipes a JOIN swipes b
                  ON a.user_id=b.target_user_id AND a.target_user_id=b.user_id
                WHERE a.user_id=:user_id AND a.target_user_id=:target_user_id
                  AND a.direction='like' AND b.direction='like'
                """
            ),
            {"user_id": user_id, "target_user_id": target_user_id},
        )
        return result.first() is not None


def get_matches(user_id):
    with engine.connect() as conn:
        return _rows(
            conn.execute(
                text(
                    """
                    SELECT u.* FROM users u
                    JOIN swipes s ON s.target_user_id=u.id
                    JOIN swipes reverse ON reverse.user_id=u.id AND reverse.target_user_id=s.user_id
                    WHERE s.user_id=:user_id AND s.direction='like' AND reverse.direction='like'
                    ORDER BY reverse.created_at DESC
                    """
                ),
                {"user_id": user_id},
            )
        )


def invalidate_user_reset_tokens(user_id):
    with engine.begin() as conn:
        conn.execute(text("UPDATE password_reset_tokens SET used=1 WHERE user_id=:id AND used=0"), {"id": user_id})


def create_password_reset_token(user_id, token_hash, expires_at):
    with engine.begin() as conn:
        conn.execute(text("UPDATE password_reset_tokens SET used=1 WHERE user_id=:id AND used=0"), {"id": user_id})
        result = conn.execute(
            text(
                """
                INSERT INTO password_reset_tokens(user_id,token_hash,expires_at,used,created_at)
                VALUES (:user_id,:token_hash,:expires_at,0,:created_at)
                RETURNING id
                """
            ),
            {"user_id": user_id, "token_hash": token_hash, "expires_at": expires_at, "created_at": utc_now_iso()},
        )
        return result.scalar_one()


def get_valid_password_reset_token(token_hash):
    with engine.connect() as conn:
        row = _row(
            conn.execute(
                text("SELECT * FROM password_reset_tokens WHERE token_hash=:token_hash AND used=0"),
                {"token_hash": token_hash},
            )
        )
    if row is None:
        return None
    try:
        expires_at = datetime.fromisoformat(row["expires_at"])
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= datetime.now(timezone.utc):
            return None
    except Exception:
        return None
    return row


def consume_password_reset_token(token_hash):
    with engine.begin() as conn:
        result = conn.execute(
            text("UPDATE password_reset_tokens SET used=1 WHERE token_hash=:token_hash AND used=0"),
            {"token_hash": token_hash},
        )
        return result.rowcount == 1


def cleanup_expired_reset_tokens():
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM password_reset_tokens WHERE expires_at < :now OR used=1"),
            {"now": utc_now_iso()},
        )


def reset_password_with_token(token_hash, new_password_hash):
    """Atomically validate, update the password, and consume a reset token."""
    if IS_SQLITE:
        # BEGIN IMMEDIATE serializes writers, preserving the original atomic reset
        # behavior on the local SQLite development database.
        with engine.connect() as conn:
            try:
                conn.exec_driver_sql("BEGIN IMMEDIATE")
                token_row = _row(
                    conn.execute(
                        text("SELECT id,user_id,expires_at FROM password_reset_tokens WHERE token_hash=:token_hash AND used=0"),
                        {"token_hash": token_hash},
                    )
                )
                _reset_transaction(conn, token_row, new_password_hash)
                conn.commit()
                return True
            except Exception:
                conn.rollback()
                raise

    with engine.begin() as conn:
        token_row = _row(
            conn.execute(
                text(
                    "SELECT id,user_id,expires_at FROM password_reset_tokens WHERE token_hash=:token_hash AND used=0 FOR UPDATE"
                ),
                {"token_hash": token_hash},
            )
        )
        _reset_transaction(conn, token_row, new_password_hash)
        return True


def _reset_transaction(conn: Connection, token_row: RowMapping | None, new_password_hash: str) -> None:
    if token_row is None:
        raise ValueError("This reset link is invalid, expired or has already been used.")

    try:
        expires_at = datetime.fromisoformat(token_row["expires_at"])
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        raise ValueError("This reset link is invalid or has expired.")

    if datetime.now(timezone.utc) >= expires_at:
        raise ValueError("This reset link is invalid or has expired.")

    user_row = _row(conn.execute(text("SELECT id FROM users WHERE id=:id"), {"id": token_row["user_id"]}))
    if user_row is None:
        raise ValueError("The account associated with this reset link no longer exists.")

    password_cursor = conn.execute(
        text("UPDATE users SET password_hash=:password_hash WHERE id=:id"),
        {"password_hash": new_password_hash, "id": token_row["user_id"]},
    )
    if password_cursor.rowcount != 1:
        raise RuntimeError("Password update failed. No account was updated.")

    token_cursor = conn.execute(
        text("UPDATE password_reset_tokens SET used=1 WHERE id=:id AND used=0"),
        {"id": token_row["id"]},
    )
    if token_cursor.rowcount != 1:
        raise RuntimeError("Password reset token could not be consumed.")


def get_user_by_photo_path(photo_path: str):
    with engine.connect() as conn:
        return _row(conn.execute(text("SELECT * FROM users WHERE photo_path=:photo_path LIMIT 1"), {"photo_path": photo_path}))
