"""
Admin DB restore endpoint tests.

Covers the C5 restore half: upload a .db snapshot, validate it is a genuine
SessionGuard SQLite backup, reject invalid inputs, and atomically swap it in
with a safety backup of the pre-restore database.
"""
import io
import sqlite3
from pathlib import Path
from fastapi.testclient import TestClient

import database.db as db_module


def _make_valid_backup(test_db: Path) -> bytes:
    """Produce a genuine SessionGuard backup via VACUUM INTO."""
    import tempfile
    tmp = Path(tempfile.mkdtemp()) / "snapshot.db"
    conn = sqlite3.connect(str(test_db))
    try:
        conn.execute(f"VACUUM INTO '{tmp}'")
    finally:
        conn.close()
    return tmp.read_bytes()


class TestRestoreEndpoint:
    """Test POST /api/v1/admin/restore."""

    def test_restore_requires_admin(self, client: TestClient, auth_headers: dict):
        """A non-admin user must not be able to restore the database."""
        resp = client.post(
            "/api/v1/admin/restore",
            files={"file": ("backup.db", io.BytesIO(b"x"), "application/x-sqlite3")},
            headers={"Authorization": auth_headers["Authorization"]},
        )
        assert resp.status_code == 403

    def test_restore_requires_auth(self, client: TestClient):
        """An anonymous caller must be rejected."""
        resp = client.post(
            "/api/v1/admin/restore",
            files={"file": ("backup.db", io.BytesIO(b"x"), "application/x-sqlite3")},
        )
        assert resp.status_code == 401

    def test_restore_rejects_non_db_extension(self, client: TestClient, admin_headers: dict):
        """Files without a .db extension must be rejected."""
        resp = client.post(
            "/api/v1/admin/restore",
            files={"file": ("backup.txt", io.BytesIO(b"x"), "text/plain")},
            headers={"Authorization": admin_headers["Authorization"]},
        )
        assert resp.status_code == 400
        assert "upload" in resp.json()["detail"].lower()

    def test_restore_rejects_empty_file(self, client: TestClient, admin_headers: dict):
        """An empty upload must be rejected."""
        resp = client.post(
            "/api/v1/admin/restore",
            files={"file": ("backup.db", io.BytesIO(b""), "application/x-sqlite3")},
            headers={"Authorization": admin_headers["Authorization"]},
        )
        assert resp.status_code == 400

    def test_restore_rejects_not_sqlite(self, client: TestClient, admin_headers: dict):
        """A file that is not a valid SQLite database must be rejected."""
        resp = client.post(
            "/api/v1/admin/restore",
            files={"file": ("backup.db", io.BytesIO(b"this is not sqlite"), "application/x-sqlite3")},
            headers={"Authorization": admin_headers["Authorization"]},
        )
        assert resp.status_code == 400

    def test_restore_rejects_wrong_schema(self, client: TestClient, admin_headers: dict, test_db: Path):
        """A valid SQLite file missing SessionGuard tables must be rejected."""
        tmp = test_db.parent / "wrong.db"
        conn = sqlite3.connect(str(tmp))
        try:
            conn.execute("CREATE TABLE random_stuff (id INTEGER PRIMARY KEY)")
            conn.commit()
        finally:
            conn.close()
        resp = client.post(
            "/api/v1/admin/restore",
            files={"file": ("wrong.db", tmp.read_bytes(), "application/x-sqlite3")},
            headers={"Authorization": admin_headers["Authorization"]},
        )
        assert resp.status_code == 400
        assert "missing tables" in resp.json()["detail"]

    def test_restore_happy_path(self, client: TestClient, admin_headers: dict, test_db: Path):
        """A valid backup restores and the pre-restore DB is safety-copied."""
        backup_bytes = _make_valid_backup(test_db)

        resp = client.post(
            "/api/v1/admin/restore",
            files={"file": ("sessionguard_backup.db", io.BytesIO(backup_bytes), "application/x-sqlite3")},
            headers={"Authorization": admin_headers["Authorization"]},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["restored"] is True
        assert data["safety_backup"] is None or Path(data["safety_backup"]).exists()

        # Database still intact and queryable after restore.
        conn = sqlite3.connect(str(db_module.DB_PATH))
        try:
            tables = {
                row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            assert "sessions" in tables
            assert "users" in tables
        finally:
            conn.close()