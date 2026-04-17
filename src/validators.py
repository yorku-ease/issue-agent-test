import re

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


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
