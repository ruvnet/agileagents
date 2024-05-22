import pytest
import warnings
from fastapi import FastAPI
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from fastapi.testclient import TestClient

# Define Pydantic models to simulate your use case

class UserBase(BaseModel):
    email: EmailStr
    role: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class UserCreate(UserBase):
    password: str

class UserUpdate(UserBase):
    password: Optional[str] = None

class User(UserBase):
    id: str
    tenant_id: str
    created_at: str

    model_config = ConfigDict(from_attributes=True)

# Define a FastAPI app to include a simple endpoint using these models

app = FastAPI()

@app.post("/test")
async def test_endpoint(user: UserCreate):
    return user

# Test to capture deprecation warnings

def test_deprecation_warnings():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        client = TestClient(app)
        response = client.post("/test", json={"email": "test@example.com", "role": "user", "password": "password"})
        assert response.status_code == 200
        # Check for deprecation warnings
        for warning in w:
            print(warning.message)
            assert not issubclass(warning.category, DeprecationWarning), f"Deprecation warning found: {warning.message}"

if __name__ == "__main__":
    pytest.main(["-v", "tests/test_deprecations.py"])
