"""
backend/routes/auth.py
-----------------------
Authentication endpoints.

POST /auth/signup   — create account
POST /auth/login    — get access + refresh tokens
POST /auth/refresh  — exchange refresh token for new access token
POST /auth/logout   — revoke refresh token
GET  /auth/me       — current user profile

Maturity: Working Prototype — all endpoints functional.
Future:   OAuth2 providers (V7), rate limiting (V6), email verification (V7).
"""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, EmailStr
from typing import Optional
from backend.auth.service import (
    create_user, authenticate_user, create_access_token,
    create_refresh_token, store_refresh_token, validate_refresh_token,
    revoke_refresh_token, get_current_user_from_token, write_audit,
)

router = APIRouter(tags=["auth"])


class SignupRequest(BaseModel):
    email:    str
    username: str
    password: str


class LoginRequest(BaseModel):
    email:    str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


# ── Signup ────────────────────────────────────────────────────────────────────
@router.post("/signup", status_code=201)
def signup(body: SignupRequest):
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")
    result = create_user(
        email=body.email,
        username=body.username,
        password=body.password,
    )
    if not result["success"]:
        raise HTTPException(status_code=409, detail=result["error"])

    user_id = result["user_id"]
    write_audit(user_id, "signup", "users", {"email": body.email})
    return {"message": "Account created.", "user_id": user_id}


# ── Login ─────────────────────────────────────────────────────────────────────
@router.post("/login")
def login(body: LoginRequest):
    user = authenticate_user(body.email, body.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token              = create_access_token(user["id"], user["email"], user["role"])
    raw_refresh, refresh_hash = create_refresh_token(user["id"])
    store_refresh_token(user["id"], refresh_hash)

    write_audit(user["id"], "login", "auth")

    return {
        "access_token":  access_token,
        "refresh_token": raw_refresh,
        "token_type":    "bearer",
        "expires_in":    3600,
        "user": {
            "id":       user["id"],
            "email":    user["email"],
            "username": user["username"],
            "role":     user["role"],
        },
    }


# ── Refresh ───────────────────────────────────────────────────────────────────
@router.post("/refresh")
def refresh(body: RefreshRequest):
    user = validate_refresh_token(body.refresh_token)
    if not user:
        raise HTTPException(status_code=401, detail="Refresh token invalid or expired.")

    # Rotate refresh token
    revoke_refresh_token(body.refresh_token)
    raw_refresh, refresh_hash = create_refresh_token(user["id"])
    store_refresh_token(user["id"], refresh_hash)

    access_token = create_access_token(user["id"], user["email"], user["role"])
    return {
        "access_token":  access_token,
        "refresh_token": raw_refresh,
        "token_type":    "bearer",
        "expires_in":    3600,
    }


# ── Logout ────────────────────────────────────────────────────────────────────
@router.post("/logout")
def logout(body: RefreshRequest, authorization: Optional[str] = Header(None)):
    revoke_refresh_token(body.refresh_token)
    current = get_current_user_from_token(authorization)
    if current:
        write_audit(current["user_id"], "logout", "auth")
    return {"message": "Logged out."}


# ── Me ────────────────────────────────────────────────────────────────────────
@router.get("/me")
def me(authorization: Optional[str] = Header(None)):
    current = get_current_user_from_token(authorization)
    if not current:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    from backend.auth.service import get_user_by_id
    user = get_user_by_id(current["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


# ── Admin: list users (admin role only) ───────────────────────────────────────
@router.get("/users")
def list_users(authorization: Optional[str] = Header(None)):
    current = get_current_user_from_token(authorization)
    if not current or current["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    from database.db import get_connection
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, email, username, role, is_active, created_at, last_login FROM users ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
