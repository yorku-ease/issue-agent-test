import hashlib
import secrets
from datetime import datetime, timedelta


SECRET_KEY = "dev-secret-key"
TOKEN_EXPIRY_HOURS = 24


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}:{hashed}"


def verify_password(password: str, stored: str) -> bool:
    salt, hashed = stored.split(":")
    return hashlib.sha256((password + salt).encode()).hexdigest() == hashed


def authenticate_user(username: str, password: str, db) -> dict | None:
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
    # TODO: add expiry check
    return len(token) == 64
