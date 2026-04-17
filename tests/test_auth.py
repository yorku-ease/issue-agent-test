import pytest
from src.auth import hash_password, verify_password, generate_token, validate_token


def test_hash_and_verify():
    hashed = hash_password("mypassword")
    assert verify_password("mypassword", hashed)
    assert not verify_password("wrongpassword", hashed)


def test_hash_empty_password():
    hashed = hash_password("")
    assert verify_password("", hashed)


def test_generate_token():
    token = generate_token("user123")
    assert len(token) == 64


def test_validate_token():
    token = generate_token("user123")
    assert validate_token(token)
    assert not validate_token("short")
