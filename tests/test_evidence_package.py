"""Regression tests for evidence package manifest integrity."""

import hashlib
import json
import zipfile

from backend.services.evidence_package import _generate_manifest, verify_evidence_manifest


def _write_archive(path, filename="events.csv", content=b"timestamp,bet\n"):
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(filename, content)


def test_manifest_round_trip_is_verified(tmp_path):
    archive_path = tmp_path / "evidence.zip"
    _write_archive(archive_path)

    manifest = _generate_manifest(str(archive_path))
    with zipfile.ZipFile(archive_path, "a") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))

    assert verify_evidence_manifest(str(archive_path)) == {"events.csv": "ok"}


def test_manifest_detects_tampering(tmp_path):
    archive_path = tmp_path / "tampered.zip"
    original = b"original"
    _write_archive(archive_path, content=b"changed")
    manifest = {"events.csv": hashlib.sha256(original).hexdigest()}

    with zipfile.ZipFile(archive_path, "a") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))

    assert verify_evidence_manifest(str(archive_path))["events.csv"] == "tampered"


def test_manifest_reports_missing_files(tmp_path):
    archive_path = tmp_path / "missing.zip"
    _write_archive(archive_path)
    manifest = {"removed.csv": hashlib.sha256(b"gone").hexdigest()}

    with zipfile.ZipFile(archive_path, "a") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))

    assert verify_evidence_manifest(str(archive_path)) == {"removed.csv": "not_found"}


def test_build_evidence_package_writes_core_contents(monkeypatch, tmp_path):
    import backend.services.evidence_package as evidence_package

    class Cursor:
        lastrowid = 42

        def fetchall(self):
            return self.rows

    class Connection:
        def __init__(self):
            self.closed = False

        def execute(self, query, _params=()):
            cursor = Cursor()
            if "FROM events" in query:
                cursor.rows = [{"timestamp": "2024-01-01T00:00:00", "win_amount": 10}]
            elif "FROM ocr_results" in query or "FROM uploads" in query:
                cursor.rows = []
            else:
                cursor.rows = []
            return cursor

        def commit(self):
            pass

        def close(self):
            self.closed = True

    connection = Connection()
    monkeypatch.setattr(evidence_package, "EXPORTS_DIR", tmp_path)
    monkeypatch.setattr(evidence_package, "get_connection", lambda: connection)
    monkeypatch.setattr(
        evidence_package,
        "get_session_metrics",
        lambda _session_id: {
            "name": "Test session",
            "game_name": "Test game",
            "platform": "desktop",
            "date": "2024-01-01",
            "net_result": 10.0,
            "rtp": 100.0,
            "spins": 1,
            "total_bets": 5.0,
            "biggest_win": 10.0,
            "losing_streak": 0,
        },
    )
    monkeypatch.setattr(evidence_package, "get_insights", lambda **_kwargs: [{"text": "steady"}])
    monkeypatch.setattr(evidence_package, "get_alerts", lambda **_kwargs: [])
    monkeypatch.setattr(evidence_package, "get_review_queue", lambda **_kwargs: [])
    monkeypatch.setattr(evidence_package, "_get_ai_narrative", lambda _session_id: None)
    monkeypatch.setattr(
        "backend.services.export_service.generate_pdf",
        lambda **_kwargs: {"success": False, "file_path": ""},
    )

    result = evidence_package.build_evidence_package(7)

    assert result["success"] is True
    assert result["export_id"] == 42
    assert connection.closed is True
    with zipfile.ZipFile(result["file_path"]) as archive:
        names = set(archive.namelist())
        assert {"manifest.json", "README.txt", "metadata/session.json", "data/events.csv", "data/insights.json"} <= names
        assert json.loads(archive.read("metadata/session.json"))["session_id"] == 7
