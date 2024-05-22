import pytest
from httpx import AsyncClient, ASGITransport
from app import app  # Import the FastAPI app from app.py

@pytest.mark.asyncio
async def test_login():
    transport = ASGITransport(app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/users/api/login", json={"email": "test@example.com", "password": "fakehashedpassword"})
        assert response.status_code == 200
        response_json = response.json()
        assert "access_token" in response_json.get("user_data", {})
        assert response_json["user_data"]["token_type"] == "bearer"

if __name__ == "__main__":
    pytest.main(["-v", "test_auth.py"])
