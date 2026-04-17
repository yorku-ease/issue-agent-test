import sqlite3
from contextlib import contextmanager


DB_PATH = "app.db"
_connection = None


def get_connection():
    global _connection
    if _connection is None:
        _connection = sqlite3.connect(DB_PATH)
    return _connection


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
        cur.execute(f"SELECT * FROM users WHERE username = '{username}'")
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
