# tests/test_users.py

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app import app
from utils.auth import get_current_user, User
from tests.mock_data import mock_users, mock_user, mock_new_user

@pytest.fixture(scope="module")
def client():
    def override_get_current_user():
        return User(email="test@example.com")
    
    app.dependency_overrides[get_current_user] = override_get_current_user
    with TestClient(app) as c:
        yield c

def get_auth_headers():
    return {
        "Authorization": "Bearer mocktoken"
    }

@patch("httpx.AsyncClient.get", new_callable=AsyncMock)
def test_read_users(mock_get, client):
    mock_get.return_value.json.return_value = mock_users
    mock_get.return_value.status_code = 200

    headers = get_auth_headers()
    response = client.get("/users", headers=headers)

    assert response.status_code == 200
    assert response.json() == mock_users

@patch("httpx.AsyncClient.get", new_callable=AsyncMock)
def test_read_user(mock_get, client):
    mock_get.return_value.json.return_value = mock_user
    mock_get.return_value.status_code = 200

    headers = get_auth_headers()
    response = client.get("/users/1", headers=headers)

    assert response.status_code == 200
    assert response.json() == mock_user

@patch("httpx.AsyncClient.post", new_callable=AsyncMock)
def test_create_user(mock_post, client):
    mock_post.return_value.json.return_value = mock_new_user
    mock_post.return_value.status_code = 201

    headers = get_auth_headers()
    user_data = {
        "email": "newuser@example.com",
        "password": "newpassword",
        "role": "user"
    }
    response = client.post("/users", json=user_data, headers=headers)

    assert response.status_code == 201
    assert response.json() == mock_new_user

@patch("httpx.AsyncClient.patch", new_callable=AsyncMock)
def test_update_user(mock_patch, client):
    mock_patch.return_value.json.return_value = mock_user
    mock_patch.return_value.status_code = 200

    headers = get_auth_headers()
    user_data = {
        "email": "updateduser@example.com",
        "role": "admin"
    }
    response = client.patch("/users/1", json=user_data, headers=headers)

    assert response.status_code == 200
    assert response.json() == mock_user

@patch("httpx.AsyncClient.delete", new_callable=AsyncMock)
def test_delete_user(mock_delete, client):
    mock_delete.return_value.status_code = 204

    headers = get_auth_headers()
    response = client.delete("/users/1", headers=headers)

    assert response.status_code == 204
