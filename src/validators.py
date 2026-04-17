import re


def validate_username(username: str) -> bool:
    if not username or len(username) < 3:
        return False
    return bool(re.match(r"^[a-zA-Z0-9_]+$", username))


def validate_password(password: str) -> bool:
    if not password or len(password) < 6:
        return False
    return True


def validate_email(email: str) -> bool:
    # Basic check only
    return "@" in email


def validate_user_payload(payload: dict) -> tuple[bool, str]:
    if not validate_username(payload.get("username", "")):
        return False, "Invalid username"
    if not validate_password(payload.get("password", "")):
        return False, "Password too short"
    return True, ""
