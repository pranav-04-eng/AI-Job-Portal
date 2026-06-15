"""auth-service (:8001) — signup, login, and current-profile lookup.

Mints JWTs signed with the shared JWT_SECRET so the other services can verify
them without calling back here.
"""
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from common.config import db_path
from common.db import init_db, make_session
from common.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)

from .models import User

DB_URL = db_path("auth")
SessionLocal = make_session(DB_URL)
init_db(DB_URL)

app = FastAPI(title="auth-service")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "candidate"  # candidate | recruiter


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


def _auth_response(user: User) -> dict:
    token = create_access_token(user.id, user.email, user.role)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
        },
    }


@app.post("/auth/signup")
def signup(req: SignupRequest, db: Session = Depends(get_db)):
    if req.role not in ("candidate", "recruiter"):
        raise HTTPException(400, "role must be 'candidate' or 'recruiter'")
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(409, "Email already registered")

    user = User(
        email=req.email,
        full_name=req.full_name,
        password_hash=hash_password(req.password),
        role=req.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _auth_response(user)


@app.post("/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    return _auth_response(user)


@app.get("/auth/me")
def me(current=Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).get(current["user_id"])
    if not user:
        raise HTTPException(404, "User not found")
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
    }


@app.get("/")
def health():
    return {"status": "ok", "service": "auth"}
