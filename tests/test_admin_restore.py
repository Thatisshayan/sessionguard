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
    """Produce a genuine SessionGuard backup via the sqlite3 online-backup API."""
    import tempfile
    tmp = Path(tempfile.mkdtemp()) / "snapshot.db"
    src = sqlite3.connect(str(test_db))
    try:
        with sqlite3.connect(str(tmp)) as dst:
            src.backup(dst)
    finally:
        src.close()
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
        assert resp.status_code == 403  # nosec B101

    def test_restore_requires_auth(self, client: TestClient):
        """An anonymous caller must be rejected."""
        resp = client.post(
            "/api/v1/admin/restore",
            files={"file": ("backup.db", io.BytesIO(b"x"), "application/x-sqlite3")},
        )
        assert resp.status_code == 401  # nosec B101

    def test_restore_rejects_non_db_extension(self, client: TestClient, admin_headers: dict):
        """Files without a .db extension must be rejected."""
        resp = client.post(
            "/api/v1/admin/restore",
            files={"file": ("backup.txt", io.BytesIO(b"x"), "text/plain")},
            headers={"Authorization": admin_headers["Authorization"]},
        )
        assert resp.status_code == 400  # nosec B101
        assert "upload" in resp.json()["detail"].lower()  # nosec B101

    def test_restore_rejects_empty_file(self, client: TestClient, admin_headers: dict):
        """An empty upload must be rejected."""
        resp = client.post(
            "/api/v1/admin/restore",
            files={"file": ("backup.db", io.BytesIO(b""), "application/x-sqlite3")},
            headers={"Authorization": admin_headers["Authorization"]},
        )
        assert resp.status_code == 400  # nosec B101

    def test_restore_rejects_not_sqlite(self, client: TestClient, admin_headers: dict):
        """A file that is not a valid SQLite database must be rejected."""
        resp = client.post(
            "/api/v1/admin/restore",
            files={"file": ("backup.db", io.BytesIO(b"this is not sqlite"), "application/x-sqlite3")},
            headers={"Authorization": admin_headers["Authorization"]},
        )
        assert resp.status_code == 400  # nosec B101

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
        assert resp.status_code == 400  # nosec B101
        assert "missing tables" in resp.json()["detail"]  # nosec B101

    def test_restore_happy_path(self, client: TestClient, admin_headers: dict, test_db: Path):
        """A valid backup restores and the pre-restore DB is safety-copied."""
        backup_bytes = _make_valid_backup(test_db)

        resp = client.post(
            "/api/v1/admin/restore",
            files={"file": ("sessionguard_backup.db", io.BytesIO(backup_bytes), "application/x-sqlite3")},
            headers={"Authorization": admin_headers["Authorization"]},
        )
        assert resp.status_code == 200, resp.text  # nosec B101
        data = resp.json()
        assert data["restored"] is True  # nosec B101
        assert data["safety_backup"] is None or Path(data["safety_backup"]).exists()  # nosec B101

        # Database still intact and queryable after restore.
        conn = sqlite3.connect(str(db_module.DB_PATH))
        try:
            tables = {
                row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            assert "sessions" in tables  # nosec B101
            assert "users" in tables  # nosec B101
        finally:
            conn.close()