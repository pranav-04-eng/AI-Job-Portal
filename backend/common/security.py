"""JWT minting/verification + password hashing, shared across services.

auth-service mints tokens; every other service verifies them with the same
JWT_SECRET via the `get_current_user` FastAPI dependency.
"""
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from common.config import JWT_ALGORITHM, JWT_EXPIRE_MINUTES, JWT_SECRET

_bearer = HTTPBearer(auto_error=True)


def hash_password(password: str) -> str:
    # bcrypt works on bytes and silently truncates past 72 bytes, so cap the
    # input explicitly rather than let long passwords hash inconsistently.
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: int, email: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    """FastAPI dependency. Returns {user_id, email, role} or raises 401."""
    try:
        payload = decode_token(creds.credentials)
        return {
            "user_id": int(payload["sub"]),
            "email": payload.get("email"),
            "role": payload.get("role", "candidate"),
        }
    except (JWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_recruiter(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] != "recruiter":
        raise HTTPException(status_code=403, detail="Recruiter role required")
    return user
