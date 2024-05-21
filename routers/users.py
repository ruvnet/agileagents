# routers/users.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import os
import httpx
from dotenv import load_dotenv
from datetime import timedelta
from utils.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    Token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    TokenData,
)
from fastapi.security import OAuth2PasswordRequestForm

# Load environment variables from .env file
load_dotenv()

# Supabase configurations
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Define Pydantic models
class UserBase(BaseModel):
    email: EmailStr
    role: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(UserBase):
    password: Optional[str] = None

class User(UserBase):
    id: str
    tenant_id: str
    created_at: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str

# Create a router instance
router = APIRouter()

# Helper function to get headers
def get_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

# Token endpoint for user authentication
@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Read all users
@router.get("/users", response_model=List[User])
async def read_users(current_user: TokenData = Depends(get_current_user)):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/users?select=*",
            headers=get_headers()
        )
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)

# Read specific user by id
@router.get("/users/{user_id}", response_model=User)
async def read_user(user_id: str, current_user: TokenData = Depends(get_current_user)):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SUPABASE_URL}/rest/v1/users?id=eq.{user_id}&select=*",
            headers=get_headers()
        )
        if response.status_code == 200:
            return response.json()[0]
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)

# Create a new user
@router.post("/users", response_model=User)
async def create_user(user: UserCreate, current_user: TokenData = Depends(get_current_user)):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SUPABASE_URL}/rest/v1/users",
            json=user.dict(),
            headers=get_headers()
        )
        if response.status_code == 201:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)

# Update an existing user
@router.patch("/users/{user_id}", response_model=User)
async def update_user(user_id: str, user: UserUpdate, current_user: TokenData = Depends(get_current_user)):
    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{SUPABASE_URL}/rest/v1/users?id=eq.{user_id}",
            json=user.dict(exclude_unset=True),
            headers=get_headers()
        )
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)

# Delete a user
@router.delete("/users/{user_id}")
async def delete_user(user_id: str, current_user: TokenData = Depends(get_current_user)):
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{SUPABASE_URL}/rest/v1/users?id=eq.{user_id}",
            headers=get_headers()
        )
        if response.status_code == 204:
            return {"message": "User deleted successfully"}
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)