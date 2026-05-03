"""
backend/auth/service.py
------------------------
Authentication service.

Password hashing: PBKDF2-HMAC-SHA256 via stdlib hashlib (no passlib/bcrypt needed).
JWT: PyJWT 2.x (already installed).

Maturity: Working Prototype — production-grade hashing, JWT with refresh tokens.
Future:   Add OAuth2 providers (V7), MFA (V8), SSO (V14).
"""

from __future__ import annotations
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timezone, timedelta
from pathlib import Path

import jwt

from database.db import get_connection

# ── Config ────────────────────────────────────────────────────────────────────
_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "app_config.json"

def _load_secret() -> str:
    try:
        with open(_CONFIG_PATH) as f:
            cfg = json.load(f)
        return cfg.get("auth", {}).get("secret_key", "")
    except Exception:
        return ""

# Secret key — loaded from config or generated fresh per process (rotate in production)
_SECRET_KEY: str = _load_secret() or secrets.token_hex(32)
_ALGORITHM        = "HS256"
ACCESS_EXPIRE_MIN  = 60          # 1 hour
REFRESH_EXPIRE_DAYS = 30


# ── Password hashing ──────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """
    Hash password using PBKDF2-HMAC-SHA256 with a random salt.
    Format: pbkdf2:sha256:{iterations}${salt_hex}${hash_hex}
    """
    salt       = os.urandom(16)
    iterations = 260_000
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"pbkdf2:sha256:{iterations}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Constant-time password verification."""
    try:
        _, _, rest  = stored.split(":", 2)
        iterations_str, salt_hex, hash_hex = rest.split("$")
        iterations  = int(iterations_str)
        salt        = bytes.fromhex(salt_hex)
        expected    = bytes.fromhex(hash_hex)
        computed    = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
        return hmac.compare_digest(computed, expected)
    except Exception:
        return False


# ── JWT tokens ────────────────────────────────────────────────────────────────

def create_access_token(user_id: int, email: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub":   str(user_id),
        "email": email,
        "role":  role,
        "iat":   now,
        "exp":   now + timedelta(minutes=ACCESS_EXPIRE_MIN),
        "type":  "access",
    }
    return jwt.encode(payload, _SECRET_KEY, algorithm=_ALGORITHM)


def create_refresh_token(user_id: int) -> tuple[str, str]:
    """
    Create a refresh token. Returns (raw_token, token_hash).
    Only the hash is stored in DB — raw token sent to client once.
    """
    raw       = secrets.token_urlsafe(48)
    tok_hash  = hashlib.sha256(raw.encode()).hexdigest()
    return raw, tok_hash


def decode_access_token(token: str) -> dict | None:
    """Decode and validate access token. Returns payload or None."""
    try:
        payload = jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# ── User operations ───────────────────────────────────────────────────────────

def create_user(email: str, username: str, password: str, role: str = "user") -> dict:
    conn = get_connection()
    existing = conn.execute(
        "SELECT id FROM users WHERE email=? OR username=?", (email, username)
    ).fetchone()
    if existing:
        conn.close()
        return {"success": False, "error": "Email or username already exists."}
    try:
        cur = conn.execute(
            "INSERT INTO users (email, username, hashed_password, role) VALUES (?,?,?,?)",
            (email.lower().strip(), username.strip(), hash_password(password), role)
        )
        user_id = cur.lastrowid
        conn.commit()
        conn.close()
        return {"success": True, "user_id": user_id}
    except Exception as e:
        conn.close()
        return {"success": False, "error": str(e)}


def authenticate_user(email: str, password: str) -> dict | None:
    """Return user dict if credentials valid, else None."""
    conn = get_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE email=? AND is_active=1",
        (email.lower().strip(),)
    ).fetchone()
    if not user:
        conn.close()
        return None
    if not verify_password(password, user["hashed_password"]):
        conn.close()
        return None
    conn.execute(
        "UPDATE users SET last_login=datetime('now') WHERE id=?", (user["id"],)
    )
    conn.commit()
    conn.close()
    return dict(user)


def get_user_by_id(user_id: int) -> dict | None:
    conn = get_connection()
    row  = conn.execute(
        "SELECT id, email, username, role, is_active, created_at, last_login FROM users WHERE id=?",
        (user_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def store_refresh_token(user_id: int, token_hash: str):
    expires = (datetime.now(timezone.utc) + timedelta(days=REFRESH_EXPIRE_DAYS)).isoformat()
    conn = get_connection()
    conn.execute(
        "INSERT INTO refresh_tokens (user_id, token_hash, expires_at) VALUES (?,?,?)",
        (user_id, token_hash, expires)
    )
    conn.commit()
    conn.close()


def validate_refresh_token(raw_token: str) -> dict | None:
    """Returns user dict if refresh token valid and not expired."""
    tok_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    conn     = get_connection()
    row      = conn.execute(
        "SELECT r.user_id, r.expires_at FROM refresh_tokens r WHERE r.token_hash=?",
        (tok_hash,)
    ).fetchone()
    if not row:
        conn.close()
        return None
    if datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc):
        conn.execute("DELETE FROM refresh_tokens WHERE token_hash=?", (tok_hash,))
        conn.commit()
        conn.close()
        return None
    user = get_user_by_id(row["user_id"])
    conn.close()
    return user


def revoke_refresh_token(raw_token: str):
    tok_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    conn = get_connection()
    conn.execute("DELETE FROM refresh_tokens WHERE token_hash=?", (tok_hash,))
    conn.commit()
    conn.close()


def write_audit(user_id: int | None, action: str, resource: str = "", detail: dict | None = None):
    conn = get_connection()
    conn.execute(
        "INSERT INTO audit_log (user_id, action, resource, detail) VALUES (?,?,?,?)",
        (user_id, action, resource, json.dumps(detail or {}))
    )
    conn.commit()
    conn.close()


# ── FastAPI dependency ────────────────────────────────────────────────────────

def get_current_user_from_token(authorization: str | None) -> dict | None:
    """
    Extract and validate Bearer token from Authorization header.
    Returns user payload dict or None.
    Usage in routes: Header(None, alias="Authorization")
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token   = authorization.split(" ", 1)[1]
    payload = decode_access_token(token)
    if not payload:
        return None
    return {
        "user_id": int(payload["sub"]),
        "email":   payload["email"],
        "role":    payload["role"],
    }
