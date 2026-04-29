"""
db/database.py — SQLite persistence layer for TrustLLM.

Tables:
    users         — Google OAuth users (also supports local test user)
    query_history — per-user query log with page, query text, and response
"""

import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "trustllm.db"


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

def init_db() -> None:
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id           TEXT PRIMARY KEY,
                name         TEXT NOT NULL,
                email        TEXT,
                picture      TEXT,
                created_at   TEXT NOT NULL,
                last_active  TEXT NOT NULL,
                query_count  INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS query_history (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    TEXT    NOT NULL,
                page       TEXT    NOT NULL,
                query      TEXT    NOT NULL,
                response   TEXT    NOT NULL DEFAULT '',
                timestamp  TEXT    NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE INDEX IF NOT EXISTS idx_qh_user_ts
                ON query_history (user_id, timestamp DESC);
        """)


# ---------------------------------------------------------------------------
# User helpers
# ---------------------------------------------------------------------------

def upsert_user(user_info: dict) -> dict:
    """Insert or update a user record; return the current DB row as dict."""
    now = datetime.utcnow().isoformat(timespec="seconds")
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO users (id, name, email, picture, created_at, last_active)
            VALUES (:id, :name, :email, :picture, :now, :now)
            ON CONFLICT(id) DO UPDATE SET
                name        = excluded.name,
                email       = excluded.email,
                picture     = excluded.picture,
                last_active = excluded.last_active
            """,
            {
                "id":      user_info["id"],
                "name":    user_info.get("name", ""),
                "email":   user_info.get("email", ""),
                "picture": user_info.get("picture", ""),
                "now":     now,
            },
        )
    return get_user(user_info["id"])


def get_user(user_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None


def touch_user(user_id: str) -> None:
    """Update last_active timestamp."""
    now = datetime.utcnow().isoformat(timespec="seconds")
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET last_active = ? WHERE id = ?", (now, user_id)
        )


# ---------------------------------------------------------------------------
# Query history helpers
# ---------------------------------------------------------------------------

def save_query(user_id: str, page: str, query: str, response: str = "") -> None:
    """Append a query to history and increment the user's query count."""
    now = datetime.utcnow().isoformat(timespec="seconds")
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO query_history (user_id, page, query, response, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, page, query, response, now),
        )
        conn.execute(
            "UPDATE users SET query_count = query_count + 1, last_active = ? WHERE id = ?",
            (now, user_id),
        )


def get_history(user_id: str, limit: int = 100) -> list[dict]:
    """Return the most recent `limit` queries for a user, newest first."""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM query_history
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def delete_history_entry(entry_id: int, user_id: str) -> None:
    """Delete a single history row (scoped to the owning user)."""
    with _connect() as conn:
        conn.execute(
            "DELETE FROM query_history WHERE id = ? AND user_id = ?",
            (entry_id, user_id),
        )
