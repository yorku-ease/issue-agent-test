import sqlite3
import threading
from contextlib import contextmanager

DB_PATH = "app.db"
_local = threading.local()


def get_connection():
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
    return _local.conn


@contextmanager
def get_cursor():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()


def get_user(username: str) -> dict | None:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
    if not row:
        return None
    return {"id": row[0], "username": row[1], "password_hash": row[2], "email": row[3]}


def create_user(username: str, password_hash: str, email: str) -> int:
    with get_cursor() as cur:
        cur.execute(
            "INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)",
            (username, password_hash, email),
        )
        return cur.lastrowid


def init_db():
    with get_cursor() as cur:
        cur.execute(
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT
            )"""
        )
