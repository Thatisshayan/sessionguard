"""Regression tests for safe exporter failure paths and live generation."""

import sys
from pathlib import Path

import pytest

import backend.services.export_service as export_service


def test_generate_pdf_reports_missing_session(monkeypatch):
    monkeypatch.setattr(export_service, "get_session_metrics", lambda _session_id: None)

    result = export_service.generate_pdf(session_id=999999)

    assert result["success"] is False
    assert result["error"] == "Session not found."


def test_generate_excel_reports_missing_session_and_closes_connection(monkeypatch):
    class FakeConnection:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    connection = FakeConnection()
    monkeypatch.setattr(export_service, "get_session_metrics", lambda _session_id: None)
    monkeypatch.setattr(export_service, "get_connection", lambda: connection)

    result = export_service.generate_excel(session_id=999999)

    assert result["success"] is False
    assert result["error"] == "Session not found."
    assert connection.closed is True


def test_generate_pdf_import_error_returns_structured_failure(monkeypatch):
    """If ReportLab isn't installed the exporter must fail gracefully with a
    structured payload, not raise. The plan calls out export_service as the
    one feature where being wrong has regulatory consequences, so the
    no-dependency path being safe matters."""
    import builtins
    real_import = builtins.__import__

    def _block(name, *args, **kwargs):
        if name == "reportlab":
            raise ImportError("reportlab missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _block)
    # Clear any cached reportlab modules so the import paths inside generate_pdf
    # actually re-execute.
    for mod in [m for m in list(sys.modules) if m.startswith("reportlab")]:
        monkeypatch.delitem(sys.modules, mod, raising=False)
    result = export_service.generate_pdf(session_id=None)
    assert result["success"] is False
    assert "reportlab missing" in result["error"]
    assert result["file_path"] == ""


def test_generate_excel_import_error_returns_structured_failure(monkeypatch):
    import builtins
    real_import = builtins.__import__

    def _block(name, *args, **kwargs):
        if name == "openpyxl":
            raise ImportError("openpyxl missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _block)
    for mod in [m for m in list(sys.modules) if m.startswith("openpyxl")]:
        monkeypatch.delitem(sys.modules, mod, raising=False)
    result = export_service.generate_excel(session_id=None)
    assert result["success"] is False
    assert "openpyxl missing" in result["error"]
    assert result["file_path"] == ""


@pytest.fixture
def _populated_db(monkeypatch, test_db, tmp_path):
    """Seed two sessions + events and point EXPORTS_DIR at a temp dir so real
    global PDF/Excel generation runs against a tiny, deterministic dataset."""
    import database.db as db
    monkeypatch.setattr(export_service, "EXPORTS_DIR", tmp_path)
    conn = db.get_connection()
    for sid, rtp, net, streak in [(1, 96.5, 50.0, 3), (2, 88.0, -120.0, 12)]:
        conn.execute(
            "INSERT INTO sessions (name, game_name, platform, date, start_balance, "
            "end_balance, net_result, rtp, spins, total_bets, biggest_win, "
            "losing_streak, status) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (f"s{sid}", f"game{sid}", "desktop", "2026-07-2X", 1000,
             1000 + net, net, rtp, 100, 500.0, 40.0, streak, "complete")
        )
        conn.execute(
            "INSERT INTO events (session_id, event_type, timestamp, bet_amount, "
            "win_amount, balance_after, confidence_score, source) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (sid, "spin", "2026-07-24T10:00:00", 5, 25, 1025 if sid == 1 else 975, 0.9, "ocr")
        )
    conn.commit()
    conn.close()
    yield


class TestGlobalPdfExport:
    def test_global_pdf_generates_real_file(self, _populated_db, tmp_path):
        result = export_service.generate_pdf(session_id=None)
        assert result["success"] is True
        assert result["file_path"]
        path = Path(result["file_path"])
        assert path.exists()
        assert path.suffix == ".pdf"
        assert path.stat().st_size > 0


class TestGlobalExcelExport:
    def test_global_excel_generates_real_workbook(self, _populated_db, tmp_path):
        result = export_service.generate_excel(session_id=None)
        assert result["success"] is True
        assert result["file_path"]
        path = Path(result["file_path"])
        assert path.exists()
        assert path.suffix == ".xlsx"
        assert path.stat().st_size > 0


class TestSessionPdfExport:
    def test_session_pdf_generates_with_events(self, _populated_db, tmp_path):
        # session_id=1 was seeded above with one event and metrics.
        result = export_service.generate_pdf(session_id=1)
        assert result["success"] is True
        path = Path(result["file_path"])
        assert path.exists() and path.suffix == ".pdf"
        assert path.stat().st_size > 0
