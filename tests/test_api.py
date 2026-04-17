import pytest
from src.api import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200


def test_register_missing_fields(client):
    res = client.post("/register", json={"username": "ab"})
    assert res.status_code == 400


def test_login_invalid(client):
    res = client.post("/login", json={"username": "noone", "password": "wrong"})
    assert res.status_code == 401
