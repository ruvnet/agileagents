from fastapi import Depends, HTTPException, Security
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Define OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/api/token")

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class User(BaseModel):
    email: str = Field(...)
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"email": "test@example.com"}
            ]
        }
    )

class UserInDB(User):
    hashed_password: str

def verify_password(plain_password, hashed_password):
    return plain_password == hashed_password  # This is just for demonstration

def get_user(email: str):
    if email == "test@example.com":
        return UserInDB(email=email, hashed_password="fakehashedpassword")
    return None

def authenticate_user(email: str, password: str):
    user = get_user(email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    user = get_user(email=token_data.email)
    if user is None:
        raise credentials_exception
    return user

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=401, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"}
            )
        return TokenData(email=email)
    except JWTError:
        raise HTTPException(
            status_code=401, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"}
        )

def get_current_user(token: str = Depends(oauth2_scheme)):
    return verify_token(token)