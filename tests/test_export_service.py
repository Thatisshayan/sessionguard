"""Regression tests for safe exporter failure paths."""

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
