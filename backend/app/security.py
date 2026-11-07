"""Authentication (bcrypt + JWT) and role-based access dependencies.

The JWT layer is deliberately small so it can be swapped for Supabase Auth:
replace `decode_token` with Supabase JWT verification and map `sub` to users.user_id.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .models import User

bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


def create_token(user: User) -> str:
    s = get_settings()
    payload = {
        "sub": str(user.user_id),
        "role": user.user_role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=s.jwt_expiry_minutes),
    }
    return jwt.encode(payload, s.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)
) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    try:
        payload = decode_token(creds.credentials)
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    user = db.get(User, user_id)
    if user is None or user.account_status != "active":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account not active")
    return user


def require_roles(*roles: str):
    def dep(user: User = Depends(current_user)) -> User:
        if user.user_role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role for this action")
        return user

    return dep
