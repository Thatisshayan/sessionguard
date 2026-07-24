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
