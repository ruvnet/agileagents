# tests/test_auth.py

import pytest
from fastapi.testclient import TestClient
from app import app
from utils.auth import get_current_user, User

@pytest.fixture(scope="module")
def client():
    def override_get_current_user():
        return User(email="test@example.com")
    
    app.dependency_overrides[get_current_user] = override_get_current_user
    with TestClient(app) as c:
        yield c

def test_login_for_access_token(client):
    response = client.post(
        "/token",
        data={"username": "test@example.com", "password": "testpassword"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_invalid_login(client):
    response = client.post(
        "/token",
        data={"username": "wrong@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401
