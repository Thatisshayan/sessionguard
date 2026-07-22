"""
database/encryption.py
----------------------
Optional SQLCipher encryption support.
Gracefully degrades to plain SQLite if pysqlcipher3 is not installed.
"""

from __future__ import annotations
import hashlib
import os
from pathlib import Path


def _check_sqlcipher_available() -> bool:
    """Check if pysqlcipher3 is available."""
    try:
        import pysqlcipher3  # noqa: F401
        return True
    except ImportError:
        return False


SQLCIPHER_AVAILABLE = _check_sqlcipher_available()


def derive_encryption_key(password: str, salt: bytes | None = None) -> tuple[bytes, bytes]:
    """
    Derive an encryption key from a password using PBKDF2-HMAC-SHA256.
    Returns (key, salt).
    """
    if salt is None:
        salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return key, salt


def get_encryption_config() -> dict | None:
    """
    Get encryption config from app_config.json.
    Returns None if encryption is not enabled.
    """
    config_path = Path(__file__).resolve().parent.parent / "config" / "app_config.json"
    try:
        import json
        cfg = json.loads(config_path.read_text())
        encryption = cfg.get("database", {}).get("encryption", {})
        if encryption.get("enabled", False):
            return encryption
    except Exception:
        pass
    return None


def apply_sqlcipher_pragmas(conn, key: bytes) -> None:
    """
    Apply SQLCipher PRAGMA commands to a connection.
    Only works with pysqlcipher3.
    """
    if not SQLCIPHER_AVAILABLE:
        return

    key_hex = key.hex()
    conn.execute(f"PRAGMA key = \"x'{key_hex}'\"")
    conn.execute("PRAGMA cipher_page_size = 4096")
    conn.execute("PRAGMA kdf_iter = 200000")


def create_encrypted_connection(db_path: str, password: str | None = None):
    """
    Create a database connection with optional encryption.
    Falls back to plain sqlite3 if pysqlcipher3 is unavailable.
    """
    if not SQLCIPHER_AVAILABLE or password is None:
        import sqlite3
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    # Use pysqlcipher3 for encrypted connection
    from pysqlcipher3 import dbapi2 as sqlcipher

    conn = sqlcipher.connect(db_path)
    conn.row_factory = sqlcipher.Row

    # Derive key from password
    # Check if we have a stored salt
    salt = _load_salt(db_path)
    if salt:
        key, _ = derive_encryption_key(password, salt)
    else:
        key, salt = derive_encryption_key(password)
        _save_salt(db_path, salt)

    apply_sqlcipher_pragmas(conn, key)

    # Verify the connection works
    try:
        conn.execute("SELECT count(*) FROM sqlite_master")
    except Exception:
        # Wrong password or corrupted DB
        conn.close()
        raise ValueError("Wrong password or corrupted database")

    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _salt_path(db_path: str) -> Path:
    return Path(db_path + ".salt")


def _load_salt(db_path: str) -> bytes | None:
    salt_file = _salt_path(db_path)
    if salt_file.exists():
        return salt_file.read_bytes()
    return None


def _save_salt(db_path: str, salt: bytes) -> None:
    _salt_path(db_path).write_bytes(salt)
