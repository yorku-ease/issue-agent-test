"""
Creates GitHub repo with 10 issues, 10 PRs (all merged), and 4 probe issues.
Usage: GITHUB_TOKEN=<token> python setup_github.py
"""
import os
import sys
import time
import subprocess
import requests

TOKEN = os.environ.get("GITHUB_TOKEN", "")
if not TOKEN:
    print("ERROR: Set GITHUB_TOKEN environment variable")
    sys.exit(1)

OWNER = None  # filled after fetching user
REPO = "issue-agent-test"
BASE = "https://api.github.com"
HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def api(method, path, **kwargs):
    url = f"{BASE}{path}"
    resp = getattr(requests, method)(url, headers=HEADERS, **kwargs)
    if resp.status_code not in (200, 201, 204):
        print(f"  ERROR {resp.status_code} {method.upper()} {path}: {resp.text[:300]}")
        resp.raise_for_status()
    return resp.json() if resp.content else {}


def run(cmd, cwd=None):
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  CMD ERROR: {cmd}\n  {result.stderr}")
        raise RuntimeError(result.stderr)
    return result.stdout.strip()


# ── 1. Get authenticated user ──────────────────────────────────────────────
print("Fetching GitHub user...")
user = api("get", "/user")
OWNER = user["login"]
print(f"  Logged in as: {OWNER}")

# ── 2. Create GitHub repo ──────────────────────────────────────────────────
print(f"\nCreating repo {OWNER}/{REPO}...")
try:
    repo_data = api("post", "/user/repos", json={
        "name": REPO,
        "description": "Test repo for issue-agent: auth, validators, database, api, utils",
        "private": False,
        "auto_init": False,
    })
    print(f"  Created: {repo_data['html_url']}")
except Exception:
    print("  Repo may already exist, continuing...")
    repo_data = api("get", f"/repos/{OWNER}/{REPO}")

REPO_URL = f"https://{TOKEN}@github.com/{OWNER}/{REPO}.git"

# ── 3. Push initial commit to GitHub ──────────────────────────────────────
print("\nPushing initial commit...")
cwd = os.path.dirname(os.path.abspath(__file__))
try:
    run(f'git remote add origin "{REPO_URL}"', cwd=cwd)
except Exception:
    run(f'git remote set-url origin "{REPO_URL}"', cwd=cwd)
run("git branch -M main", cwd=cwd)
run("git push -u origin main", cwd=cwd)
print("  Pushed main branch.")

# ── 4. Create 10 issues ────────────────────────────────────────────────────
ISSUES = [
    {
        "title": "Bug: auth.py crashes when password is empty string",
        "body": (
            "## Description\n"
            "When a user submits an empty password during login, `auth.py` raises an unhandled "
            "exception instead of returning a proper error.\n\n"
            "## Steps to reproduce\n"
            "1. POST /login with `{\"username\": \"alice\", \"password\": \"\"}`\n"
            "2. Server crashes with `ValueError` in `src/auth.py`\n\n"
            "## Expected\nReturn 401 with error message.\n\n"
            "**Affected files:** `src/auth.py`"
        ),
    },
    {
        "title": "Feature: add proper email format validation in validators.py",
        "body": (
            "## Description\n"
            "The current `validate_email` in `src/validators.py` only checks for `@` presence. "
            "It should use a proper regex pattern to reject malformed emails like `foo@` or `@bar`.\n\n"
            "## Expected behavior\n"
            "- `foo@bar.com` → valid\n"
            "- `foo@` → invalid\n"
            "- `@bar.com` → invalid\n\n"
            "**Affected files:** `src/validators.py`"
        ),
    },
    {
        "title": "Bug: database.py uses a single global connection causing pool exhaustion",
        "body": (
            "## Description\n"
            "In `src/database.py`, `get_connection()` returns a single global `_connection`. "
            "Under concurrent load this leads to `ProgrammingError: Cannot operate on a closed database`.\n\n"
            "## Root cause\nNo connection pooling — global singleton is reused across threads.\n\n"
            "## Fix suggestion\nUse `threading.local()` or a connection pool.\n\n"
            "**Affected files:** `src/database.py`"
        ),
    },
    {
        "title": "Bug: api.py /users/<username> returns 200 instead of 404 when user not found",
        "body": (
            "## Description\n"
            "The `GET /users/<username>` endpoint in `src/api.py` returns HTTP 200 with "
            "`{\"error\": \"Not found\"}` when the user doesn't exist. It should return 404.\n\n"
            "## Expected\n`404 Not Found` with `{\"error\": \"User not found\"}`\n\n"
            "**Affected files:** `src/api.py`"
        ),
    },
    {
        "title": "Refactor: utils.py sanitize_string does not strip internal whitespace",
        "body": (
            "## Description\n"
            "`sanitize_string` in `src/utils.py` only strips leading/trailing whitespace. "
            "It should also collapse multiple internal spaces and remove control characters.\n\n"
            "## Example\n"
            "- Input: `'  hello   world  '`\n"
            "- Current output: `'hello   world'`\n"
            "- Expected output: `'hello world'`\n\n"
            "**Affected files:** `src/utils.py`"
        ),
    },
    {
        "title": "Bug: auth.py and validators.py disagree on minimum password length during registration",
        "body": (
            "## Description\n"
            "`src/validators.py:validate_password` requires length >= 6, but `src/auth.py:hash_password` "
            "accepts any length. During registration a 5-char password passes hashing but "
            "`validate_user_payload` rejects it — the order of checks is inconsistent.\n\n"
            "## Fix\nCentralize password policy in `validators.py` and enforce it in `auth.py`.\n\n"
            "**Affected files:** `src/auth.py`, `src/validators.py`"
        ),
    },
    {
        "title": "Feature: add per-IP rate limiting to api.py login endpoint",
        "body": (
            "## Description\n"
            "The `/login` endpoint in `src/api.py` has no rate limiting. Brute-force attacks are possible.\n\n"
            "## Proposed solution\n"
            "Add a sliding-window counter in `src/utils.py` and apply it as a decorator on the login route.\n\n"
            "## Acceptance criteria\n"
            "- Max 10 login attempts per IP per minute\n"
            "- Returns 429 with `Retry-After` header when exceeded\n\n"
            "**Affected files:** `src/api.py`, `src/utils.py`"
        ),
    },
    {
        "title": "Security: database.py get_user uses string interpolation — SQL injection vulnerability",
        "body": (
            "## Description\n"
            "`src/database.py:get_user` builds the SQL query with f-string interpolation:\n"
            "```python\n"
            "cur.execute(f\"SELECT * FROM users WHERE username = '{username}'\")\n"
            "```\n"
            "This is vulnerable to SQL injection. An attacker can pass `' OR '1'='1` as username.\n\n"
            "## Fix\nUse parameterized queries.\n\n"
            "**Affected files:** `src/database.py`, `src/validators.py`"
        ),
    },
    {
        "title": "Feature: implement JWT token refresh in auth.py with expiry stored in database.py",
        "body": (
            "## Description\n"
            "`src/auth.py:validate_token` has a TODO comment for expiry checking. "
            "Tokens never expire, which is a security risk.\n\n"
            "## Proposed solution\n"
            "1. Store token + expiry timestamp in a `tokens` table in `src/database.py`\n"
            "2. `validate_token` in `src/auth.py` queries the table to check expiry\n"
            "3. Add `refresh_token` endpoint\n\n"
            "**Affected files:** `src/auth.py`, `src/database.py`"
        ),
    },
    {
        "title": "Bug: api.py and database.py have no timeout handling — requests hang indefinitely",
        "body": (
            "## Description\n"
            "Database queries in `src/database.py` and API responses in `src/api.py` have no timeout. "
            "A slow query causes the Flask worker to hang, blocking all subsequent requests.\n\n"
            "## Fix\n"
            "- Set `timeout` on SQLite connection in `src/database.py`\n"
            "- Add request timeout middleware in `src/api.py`\n\n"
            "**Affected files:** `src/api.py`, `src/database.py`"
        ),
    },
]

print("\nCreating 10 issues...")
issue_numbers = []
for i, issue in enumerate(ISSUES, 1):
    result = api("post", f"/repos/{OWNER}/{REPO}/issues", json=issue)
    issue_numbers.append(result["number"])
    print(f"  Issue #{result['number']}: {issue['title'][:60]}")
    time.sleep(0.5)

# ── 5. Branch definitions: file patches per PR ───────────────────────────
def patch_file(cwd, filepath, content):
    full = os.path.join(cwd, filepath)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)

BRANCHES = [
    # PR 1 — fix auth.py empty password
    {
        "branch": "fix/auth-empty-password",
        "title": "Fix: handle empty password in auth.py",
        "body": f"Closes #{issue_numbers[0]}\n\nAdd guard for empty password in `authenticate_user` and `hash_password` to return a proper error instead of crashing.",
        "files": {
            "src/auth.py": """\
import hashlib
import secrets
from datetime import datetime, timedelta


SECRET_KEY = "dev-secret-key"
TOKEN_EXPIRY_HOURS = 24


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("Password cannot be empty")
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}:{hashed}"


def verify_password(password: str, stored: str) -> bool:
    if not password or ":" not in stored:
        return False
    salt, hashed = stored.split(":", 1)
    return hashlib.sha256((password + salt).encode()).hexdigest() == hashed


def authenticate_user(username: str, password: str, db) -> dict | None:
    if not username or not password:
        return None
    user = db.get_user(username)
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user


def generate_token(user_id: str) -> str:
    payload = f"{user_id}:{datetime.utcnow().isoformat()}"
    return hashlib.sha256((payload + SECRET_KEY).encode()).hexdigest()


def validate_token(token: str) -> bool:
    return len(token) == 64
""",
        },
        "commit_msg": "Fix empty password crash in auth.py — add guard and safe verify",
    },
    # PR 2 — fix validators.py email
    {
        "branch": "feature/email-validation",
        "title": "Feature: improve email validation in validators.py",
        "body": f"Closes #{issue_numbers[1]}\n\nReplace the bare `@` check with a proper regex in `validate_email`.",
        "files": {
            "src/validators.py": """\
import re

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+\\-]+@[a-zA-Z0-9.\\-]+\\.[a-zA-Z]{2,}$")


def validate_username(username: str) -> bool:
    if not username or len(username) < 3:
        return False
    return bool(re.match(r"^[a-zA-Z0-9_]+$", username))


def validate_password(password: str) -> bool:
    if not password or len(password) < 8:
        return False
    return True


def validate_email(email: str) -> bool:
    if not email:
        return False
    return bool(EMAIL_REGEX.match(email))


def validate_user_payload(payload: dict) -> tuple[bool, str]:
    if not validate_username(payload.get("username", "")):
        return False, "Invalid username"
    if not validate_password(payload.get("password", "")):
        return False, "Password must be at least 8 characters"
    if payload.get("email") and not validate_email(payload["email"]):
        return False, "Invalid email format"
    return True, ""
""",
        },
        "commit_msg": "Add proper regex email validation in validators.py",
    },
    # PR 3 — fix database.py connection pooling
    {
        "branch": "fix/db-connection-pool",
        "title": "Fix: use thread-local connections in database.py",
        "body": f"Closes #{issue_numbers[2]}\n\nReplace global singleton with `threading.local()` to fix connection exhaustion under concurrent load.",
        "files": {
            "src/database.py": """\
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
            \"\"\"CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT
            )\"\"\"
        )
""",
        },
        "commit_msg": "Fix database.py: thread-local connections prevent pool exhaustion",
    },
    # PR 4 — fix api.py 404
    {
        "branch": "fix/api-404-status",
        "title": "Fix: return 404 when user not found in api.py",
        "body": f"Closes #{issue_numbers[3]}\n\nFix `/users/<username>` to return proper 404 status code instead of 200.",
        "files": {
            "src/api.py": """\
from flask import Flask, request, jsonify
from src import auth, validators, database

app = Flask(__name__)


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    valid, msg = validators.validate_user_payload(data)
    if not valid:
        return jsonify({"error": msg}), 400
    password_hash = auth.hash_password(data["password"])
    user_id = database.create_user(data["username"], password_hash, data.get("email", ""))
    return jsonify({"id": user_id}), 201


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    user = auth.authenticate_user(data["username"], data["password"], database)
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401
    token = auth.generate_token(str(user["id"]))
    return jsonify({"token": token}), 200


@app.route("/users/<username>", methods=["GET"])
def get_user(username):
    user = database.get_user(username)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"username": user["username"], "email": user["email"]}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200
""",
        },
        "commit_msg": "Fix api.py: return 404 not 200 when user not found",
    },
    # PR 5 — refactor utils.py
    {
        "branch": "refactor/utils-sanitize",
        "title": "Refactor: improve sanitize_string in utils.py",
        "body": f"Closes #{issue_numbers[4]}\n\nCollapse internal whitespace and strip control characters in `sanitize_string`.",
        "files": {
            "src/utils.py": """\
import re
import time
import functools


def retry(times=3, delay=1):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            for attempt in range(times):
                try:
                    return fn(*args, **kwargs)
                except Exception:
                    if attempt == times - 1:
                        raise
                    time.sleep(delay)
        return wrapper
    return decorator


def paginate(items: list, page: int, per_page: int = 10) -> dict:
    start = page * per_page
    end = start + per_page
    return {
        "items": items[start:end],
        "page": page,
        "total": len(items),
        "pages": (len(items) + per_page - 1) // per_page,
    }


def sanitize_string(value: str) -> str:
    value = value.strip()
    value = re.sub(r"[\\x00-\\x1f\\x7f]", "", value)
    value = re.sub(r" +", " ", value)
    return value
""",
        },
        "commit_msg": "Refactor utils.py: sanitize_string collapses whitespace and strips control chars",
    },
    # PR 6 — fix auth.py + validators.py password policy conflict
    {
        "branch": "fix/password-policy-conflict",
        "title": "Fix: unify password policy between auth.py and validators.py",
        "body": f"Closes #{issue_numbers[5]}\n\nCentralize minimum password length in `validators.py` and enforce it in `auth.py` before hashing.",
        "files": {
            "src/auth.py": """\
import hashlib
import secrets
from datetime import datetime
from src.validators import validate_password


SECRET_KEY = "dev-secret-key"
TOKEN_EXPIRY_HOURS = 24


def hash_password(password: str) -> str:
    if not validate_password(password):
        raise ValueError("Password does not meet policy requirements")
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}:{hashed}"


def verify_password(password: str, stored: str) -> bool:
    if not password or ":" not in stored:
        return False
    salt, hashed = stored.split(":", 1)
    return hashlib.sha256((password + salt).encode()).hexdigest() == hashed


def authenticate_user(username: str, password: str, db) -> dict | None:
    if not username or not password:
        return None
    user = db.get_user(username)
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user


def generate_token(user_id: str) -> str:
    payload = f"{user_id}:{datetime.utcnow().isoformat()}"
    return hashlib.sha256((payload + SECRET_KEY).encode()).hexdigest()


def validate_token(token: str) -> bool:
    return len(token) == 64
""",
            "src/validators.py": """\
import re

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+\\-]+@[a-zA-Z0-9.\\-]+\\.[a-zA-Z]{2,}$")
MIN_PASSWORD_LENGTH = 8


def validate_username(username: str) -> bool:
    if not username or len(username) < 3:
        return False
    return bool(re.match(r"^[a-zA-Z0-9_]+$", username))


def validate_password(password: str) -> bool:
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        return False
    return True


def validate_email(email: str) -> bool:
    if not email:
        return False
    return bool(EMAIL_REGEX.match(email))


def validate_user_payload(payload: dict) -> tuple[bool, str]:
    if not validate_username(payload.get("username", "")):
        return False, "Invalid username"
    if not validate_password(payload.get("password", "")):
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
    if payload.get("email") and not validate_email(payload["email"]):
        return False, "Invalid email format"
    return True, ""
""",
        },
        "commit_msg": "Unify password policy: validators.py is source of truth, auth.py enforces it",
    },
    # PR 7 — rate limiting api.py + utils.py
    {
        "branch": "feature/rate-limiting",
        "title": "Feature: per-IP rate limiting on login endpoint in api.py",
        "body": f"Closes #{issue_numbers[6]}\n\nAdd sliding-window rate limiter in `utils.py` and apply it to the `/login` route in `api.py`.",
        "files": {
            "src/utils.py": """\
import re
import time
import functools
from collections import defaultdict

_rate_limit_store: dict = defaultdict(list)


def retry(times=3, delay=1):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            for attempt in range(times):
                try:
                    return fn(*args, **kwargs)
                except Exception:
                    if attempt == times - 1:
                        raise
                    time.sleep(delay)
        return wrapper
    return decorator


def paginate(items: list, page: int, per_page: int = 10) -> dict:
    start = page * per_page
    end = start + per_page
    return {
        "items": items[start:end],
        "page": page,
        "total": len(items),
        "pages": (len(items) + per_page - 1) // per_page,
    }


def sanitize_string(value: str) -> str:
    value = value.strip()
    value = re.sub(r"[\\x00-\\x1f\\x7f]", "", value)
    value = re.sub(r" +", " ", value)
    return value


def is_rate_limited(key: str, max_calls: int = 10, window_seconds: int = 60) -> bool:
    now = time.time()
    timestamps = _rate_limit_store[key]
    _rate_limit_store[key] = [t for t in timestamps if now - t < window_seconds]
    if len(_rate_limit_store[key]) >= max_calls:
        return True
    _rate_limit_store[key].append(now)
    return False
""",
            "src/api.py": """\
from flask import Flask, request, jsonify
from src import auth, validators, database
from src.utils import is_rate_limited

app = Flask(__name__)


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    valid, msg = validators.validate_user_payload(data)
    if not valid:
        return jsonify({"error": msg}), 400
    password_hash = auth.hash_password(data["password"])
    user_id = database.create_user(data["username"], password_hash, data.get("email", ""))
    return jsonify({"id": user_id}), 201


@app.route("/login", methods=["POST"])
def login():
    ip = request.remote_addr
    if is_rate_limited(ip, max_calls=10, window_seconds=60):
        return jsonify({"error": "Too many requests"}), 429
    data = request.get_json()
    user = auth.authenticate_user(data["username"], data["password"], database)
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401
    token = auth.generate_token(str(user["id"]))
    return jsonify({"token": token}), 200


@app.route("/users/<username>", methods=["GET"])
def get_user(username):
    user = database.get_user(username)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"username": user["username"], "email": user["email"]}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200
""",
        },
        "commit_msg": "Add rate limiting: sliding window counter in utils.py, applied in api.py login",
    },
    # PR 8 — SQL injection fix database.py + validators.py
    {
        "branch": "fix/sql-injection",
        "title": "Security: fix SQL injection in database.py get_user",
        "body": f"Closes #{issue_numbers[7]}\n\nReplace f-string interpolation with parameterized query. Add `validate_username` call before DB lookup in `validators.py`.",
        "files": {
            "src/database.py": """\
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
            \"\"\"CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT
            )\"\"\"
        )
""",
            "src/validators.py": """\
import re

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+\\-]+@[a-zA-Z0-9.\\-]+\\.[a-zA-Z]{2,}$")
MIN_PASSWORD_LENGTH = 8
SAFE_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,32}$")


def validate_username(username: str) -> bool:
    if not username:
        return False
    return bool(SAFE_USERNAME_RE.match(username))


def validate_password(password: str) -> bool:
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        return False
    return True


def validate_email(email: str) -> bool:
    if not email:
        return False
    return bool(EMAIL_REGEX.match(email))


def validate_user_payload(payload: dict) -> tuple[bool, str]:
    if not validate_username(payload.get("username", "")):
        return False, "Invalid username"
    if not validate_password(payload.get("password", "")):
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
    if payload.get("email") and not validate_email(payload["email"]):
        return False, "Invalid email format"
    return True, ""
""",
        },
        "commit_msg": "Security fix: parameterized queries in database.py, tighter username regex in validators.py",
    },
    # PR 9 — token expiry auth.py + database.py
    {
        "branch": "feature/token-expiry",
        "title": "Feature: token expiry and refresh in auth.py with database.py storage",
        "body": f"Closes #{issue_numbers[8]}\n\nImplement token expiry: store tokens in DB via `database.py`, validate expiry in `auth.py`.",
        "files": {
            "src/auth.py": """\
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from src.validators import validate_password

SECRET_KEY = "dev-secret-key"
TOKEN_EXPIRY_HOURS = 24


def hash_password(password: str) -> str:
    if not validate_password(password):
        raise ValueError("Password does not meet policy requirements")
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}:{hashed}"


def verify_password(password: str, stored: str) -> bool:
    if not password or ":" not in stored:
        return False
    salt, hashed = stored.split(":", 1)
    return hashlib.sha256((password + salt).encode()).hexdigest() == hashed


def authenticate_user(username: str, password: str, db) -> dict | None:
    if not username or not password:
        return None
    user = db.get_user(username)
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user


def generate_token(user_id: str) -> tuple[str, datetime]:
    token = secrets.token_hex(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRY_HOURS)
    return token, expires_at


def validate_token(token: str, db) -> bool:
    record = db.get_token(token)
    if not record:
        return False
    expires_at = datetime.fromisoformat(record["expires_at"])
    return datetime.now(timezone.utc) < expires_at
""",
            "src/database.py": """\
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime

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


def store_token(token: str, user_id: int, expires_at: datetime) -> None:
    with get_cursor() as cur:
        cur.execute(
            "INSERT INTO tokens (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user_id, expires_at.isoformat()),
        )


def get_token(token: str) -> dict | None:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM tokens WHERE token = ?", (token,))
        row = cur.fetchone()
    if not row:
        return None
    return {"token": row[0], "user_id": row[1], "expires_at": row[2]}


def init_db():
    with get_cursor() as cur:
        cur.execute(
            \"\"\"CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT
            )\"\"\"
        )
        cur.execute(
            \"\"\"CREATE TABLE IF NOT EXISTS tokens (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL
            )\"\"\"
        )
""",
        },
        "commit_msg": "Implement token expiry: generate+store in database.py, validate expiry in auth.py",
    },
    # PR 10 — timeout handling api.py + database.py
    {
        "branch": "fix/timeout-handling",
        "title": "Fix: add timeout handling in api.py and database.py",
        "body": f"Closes #{issue_numbers[9]}\n\nAdd SQLite busy timeout in `database.py` and request timeout middleware in `api.py`.",
        "files": {
            "src/database.py": """\
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime

DB_PATH = "app.db"
DB_TIMEOUT_SECONDS = 5
_local = threading.local()


def get_connection():
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(
            DB_PATH,
            check_same_thread=False,
            timeout=DB_TIMEOUT_SECONDS,
        )
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA busy_timeout = 5000")
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


def store_token(token: str, user_id: int, expires_at: datetime) -> None:
    with get_cursor() as cur:
        cur.execute(
            "INSERT INTO tokens (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user_id, expires_at.isoformat()),
        )


def get_token(token: str) -> dict | None:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM tokens WHERE token = ?", (token,))
        row = cur.fetchone()
    if not row:
        return None
    return {"token": row[0], "user_id": row[1], "expires_at": row[2]}


def init_db():
    with get_cursor() as cur:
        cur.execute(
            \"\"\"CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT
            )\"\"\"
        )
        cur.execute(
            \"\"\"CREATE TABLE IF NOT EXISTS tokens (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL
            )\"\"\"
        )
""",
            "src/api.py": """\
import signal
from flask import Flask, request, jsonify
from src import auth, validators, database
from src.utils import is_rate_limited

app = Flask(__name__)
REQUEST_TIMEOUT_SECONDS = 10


@app.before_request
def set_request_timeout():
    signal.signal(signal.SIGALRM, lambda s, f: (_ for _ in ()).throw(TimeoutError()))
    signal.alarm(REQUEST_TIMEOUT_SECONDS)


@app.teardown_request
def clear_timeout(exc=None):
    signal.alarm(0)


@app.errorhandler(TimeoutError)
def handle_timeout(e):
    return jsonify({"error": "Request timed out"}), 504


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    valid, msg = validators.validate_user_payload(data)
    if not valid:
        return jsonify({"error": msg}), 400
    password_hash = auth.hash_password(data["password"])
    user_id = database.create_user(data["username"], password_hash, data.get("email", ""))
    return jsonify({"id": user_id}), 201


@app.route("/login", methods=["POST"])
def login():
    ip = request.remote_addr
    if is_rate_limited(ip, max_calls=10, window_seconds=60):
        return jsonify({"error": "Too many requests"}), 429
    data = request.get_json()
    user = auth.authenticate_user(data["username"], data["password"], database)
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401
    token, expires_at = auth.generate_token(str(user["id"]))
    database.store_token(token, user["id"], expires_at)
    return jsonify({"token": token}), 200


@app.route("/users/<username>", methods=["GET"])
def get_user(username):
    user = database.get_user(username)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"username": user["username"], "email": user["email"]}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200
""",
        },
        "commit_msg": "Add timeout handling: busy_timeout in database.py, SIGALRM middleware in api.py",
    },
]

# ── 6. Create branches, push, open PRs, merge ─────────────────────────────
print("\nCreating branches, PRs, and merging...")
cwd = os.path.dirname(os.path.abspath(__file__))
pr_numbers = []

for i, branch_def in enumerate(BRANCHES):
    branch = branch_def["branch"]
    print(f"\n  [{i+1}/10] Branch: {branch}")

    # create branch from main
    run(f"git checkout main", cwd=cwd)
    run(f"git checkout -b {branch}", cwd=cwd)

    # write file changes
    for filepath, content in branch_def["files"].items():
        patch_file(cwd, filepath, content)

    # commit
    run("git add -A", cwd=cwd)
    run(f'git commit -m "{branch_def["commit_msg"]}"', cwd=cwd)
    run(f"git push origin {branch}", cwd=cwd)

    # create PR
    pr = api("post", f"/repos/{OWNER}/{REPO}/pulls", json={
        "title": branch_def["title"],
        "body": branch_def["body"],
        "head": branch,
        "base": "main",
    })
    pr_num = pr["number"]
    pr_numbers.append(pr_num)
    print(f"    PR #{pr_num}: {branch_def['title'][:55]}")
    time.sleep(1)

    # merge PR
    try:
        api("put", f"/repos/{OWNER}/{REPO}/pulls/{pr_num}/merge", json={
            "merge_method": "squash",
            "commit_title": branch_def["commit_msg"],
        })
        print(f"    Merged PR #{pr_num}")
    except Exception as e:
        print(f"    Could not merge PR #{pr_num}: {e}")

    # pull merged main
    run("git checkout main", cwd=cwd)
    run("git pull origin main", cwd=cwd)
    time.sleep(1)

# ── 7. Create 4 probe issues ───────────────────────────────────────────────
PROBE_ISSUES = [
    {
        "title": "[PROBE-1 FOUND] Login crashes when password contains special characters — auth.py",
        "body": (
            "## Description\n"
            "When a user sets a password with special characters like `!@#$%` and then logs in, "
            "the server crashes with an unhandled exception in `src/auth.py`.\n\n"
            "## Steps to reproduce\n"
            "1. Register with password `secret!@#`\n"
            "2. POST /login with those credentials\n"
            "3. Crash occurs inside `auth.py` verify logic\n\n"
            "## Expected\nShould authenticate successfully or return 401.\n\n"
            "**Affected files:** `src/auth.py`\n\n"
            "> **[PROBE]** This should match: issue #1 (auth.py crash), issue #6 (auth+validators), "
            "and PRs that touched auth.py"
        ),
    },
    {
        "title": "[PROBE-2 FOUND] Request timeouts not handled — api.py and database.py hang",
        "body": (
            "## Description\n"
            "Under high load, slow queries in `src/database.py` cause Flask workers in `src/api.py` "
            "to hang indefinitely. No timeout is enforced at either layer.\n\n"
            "## Impact\nAll API endpoints become unresponsive after a single slow query.\n\n"
            "## Fix suggestion\n"
            "- Add `timeout` to the SQLite connection in `src/database.py`\n"
            "- Add per-request timeout middleware in `src/api.py`\n\n"
            "**Affected files:** `src/api.py`, `src/database.py`\n\n"
            "> **[PROBE]** This should match: issue #10 (timeout), issue #3 (db connection), "
            "and PRs that touched api.py + database.py"
        ),
    },
    {
        "title": "[PROBE-3 NOT FOUND] Docker container fails to start — docker-compose.yml and Dockerfile misconfigured",
        "body": (
            "## Description\n"
            "The application Docker container fails to start due to misconfiguration in "
            "`docker-compose.yml` and `Dockerfile`. The entrypoint command is incorrect and the "
            "health check probe is hitting the wrong port.\n\n"
            "## Steps to reproduce\n"
            "1. `docker-compose up`\n"
            "2. Container exits immediately with code 1\n"
            "3. Logs show `exec format error` in `Dockerfile` entrypoint\n\n"
            "## Expected\nContainer should start and serve traffic on port 5000.\n\n"
            "**Affected files:** `docker-compose.yml`, `Dockerfile`\n\n"
            "> **[PROBE]** This should NOT match: no Docker files exist in any PR, "
            "topic is infrastructure not Python code"
        ),
    },
    {
        "title": "[PROBE-4 SPLIT] Add Prometheus metrics endpoint to api.py for observability",
        "body": (
            "## Description\n"
            "We need a `/metrics` endpoint in `src/api.py` that exposes Prometheus-compatible "
            "counters for request counts, error rates, and response latencies. "
            "This is for the new observability initiative.\n\n"
            "## Proposed implementation\n"
            "- Use `prometheus_client` library\n"
            "- Expose `http_requests_total`, `http_request_duration_seconds` metrics\n"
            "- Mount at `/metrics` in `src/api.py`\n\n"
            "**Affected files:** `src/api.py`\n\n"
            "> **[PROBE]** SPLIT RESULT: co-change should find PRs that touched api.py (#4, #7, #10), "
            "but vector search should NOT match (observability/metrics topic is unlike all 10 issues)"
        ),
    },
]

print("\n\nCreating 4 probe issues...")
probe_numbers = []
for issue in PROBE_ISSUES:
    result = api("post", f"/repos/{OWNER}/{REPO}/issues", json=issue)
    probe_numbers.append(result["number"])
    print(f"  Probe Issue #{result['number']}: {issue['title'][:70]}")
    time.sleep(0.5)

print(f"""
╔══════════════════════════════════════════════════════════════╗
║  Setup Complete!
║
║  Repo: https://github.com/{OWNER}/{REPO}
║
║  Knowledge base (closed):
║    Issues: #{', #'.join(str(n) for n in issue_numbers)}
║    PRs:    #{', #'.join(str(n) for n in pr_numbers)}
║
║  Probe issues (open — feed to issue-agent):
║    #{probe_numbers[0]} — FOUND (auth.py crash → matches PRs + issues)
║    #{probe_numbers[1]} — FOUND (api+db timeout → matches PRs + issues)
║    #{probe_numbers[2]} — NOT FOUND (Docker config → no match)
║    #{probe_numbers[3]} — SPLIT (api.py metrics → co-change found, vector not)
╚══════════════════════════════════════════════════════════════╝
""")
