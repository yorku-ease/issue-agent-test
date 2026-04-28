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
