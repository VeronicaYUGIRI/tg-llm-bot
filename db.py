import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.getenv("DB_PATH", "usage.db")


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS usage_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT,
                model TEXT NOT NULL,
                prompt_tokens INTEGER NOT NULL,
                completion_tokens INTEGER NOT NULL,
                cost REAL NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                chat_id INTEGER PRIMARY KEY,
                model TEXT NOT NULL,
                window_size INTEGER NOT NULL
            )
        """)


def log_usage(chat_id, user_id, username, model, prompt_tokens, completion_tokens, cost, timestamp):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO usage_log
               (timestamp, chat_id, user_id, username, model, prompt_tokens, completion_tokens, cost)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (timestamp, chat_id, user_id, username, model, prompt_tokens, completion_tokens, cost),
        )


def get_chat_total_cost(chat_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(cost), 0), COALESCE(SUM(prompt_tokens + completion_tokens), 0), COUNT(*) "
            "FROM usage_log WHERE chat_id = ?",
            (chat_id,),
        ).fetchone()
        return {"total_cost": row[0], "total_tokens": row[1], "call_count": row[2]}


def get_chat_settings(chat_id, default_model, default_window_size):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT model, window_size FROM settings WHERE chat_id = ?", (chat_id,)
        ).fetchone()
        if row is None:
            return {"model": default_model, "window_size": default_window_size}
        return {"model": row[0], "window_size": row[1]}


def set_chat_model(chat_id, model, default_window_size):
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT window_size FROM settings WHERE chat_id = ?", (chat_id,)
        ).fetchone()
        window_size = existing[0] if existing else default_window_size
        conn.execute(
            "INSERT INTO settings (chat_id, model, window_size) VALUES (?, ?, ?) "
            "ON CONFLICT(chat_id) DO UPDATE SET model = excluded.model",
            (chat_id, model, window_size),
        )


def set_chat_window_size(chat_id, window_size, default_model):
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT model FROM settings WHERE chat_id = ?", (chat_id,)
        ).fetchone()
        model = existing[0] if existing else default_model
        conn.execute(
            "INSERT INTO settings (chat_id, model, window_size) VALUES (?, ?, ?) "
            "ON CONFLICT(chat_id) DO UPDATE SET window_size = excluded.window_size",
            (chat_id, model, window_size),
        )
