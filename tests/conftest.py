# tests/conftest.py

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
