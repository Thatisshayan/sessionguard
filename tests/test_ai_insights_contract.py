"""Safe, fully-local contract tests for the NVIDIA NIM AI layer (Revival 1.3, B3).

The Revival 1.3 plan flags B3 (verify AI streaming against a real NVIDIA NIM
endpoint) as never-started, and finding #14 in the plan showed the whole
``ai_analysis`` router had never even been mounted. Live verification is
deferred (no approved API key, no external network). These tests pin the
*contract* that the live endpoint must satisfy, entirely with mocks — no
network and no real API key is ever touched.

Covers:
  * ``_call_nvidia`` parses a well-formed OpenAI-compatible response and
    surfaces HTTP errors as ``RuntimeError``.
  * ``_stream_nvidia`` yields ``chunk`` then ``done`` events from an SSE body
    and surfaces HTTP errors as an ``error`` event.
  * ``analyse_session_with_ai`` end-to-end with a fake API key + mocked
    transport returns ``source == "nvidia_ai"``, persists AI insights, and
    logs cost to ``ai_cost_log``.
  * With no API key and no Ollama, falls back to ``source == "rule_based"``.

No paid API call, no real NVIDIA API key, no network. Per REPO_RULES R3/R4:
B3's *live* verification against a real NVIDIA NIM endpoint is recorded in
``docs/governance/DEFERRED_WORK.md`` and called out in the plan doc.
"""

from __future__ import annotations

import io
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines import ai_insights_engine as ai
from backend.schemas.ai import parse_ai_response


VALID_AI_JSON = json.dumps({
    "headline": "Discipline held, RTP below expectation",
    "risk_level": "moderate",
    "insights": [
        {"severity": "warning", "category": "rtp", "text": "RTP 91% vs expected 96%"},
        {"severity": "info", "category": "discipline", "text": "Bet sizing stable"},
    ],
    "behaviour_summary": "Steady bet sizing; losing streak late but no escalation.",
    "notable_moments": ["Late 8-spin losing streak"],
    "discipline_score": 78,
    "one_line_verdict": "Discipline fine; variance hurt the result.",
})


def _openai_body(content: str, usage: dict | None = None) -> bytes:
    return json.dumps({
        "choices": [{"message": {"role": "assistant", "content": content}}],
        "usage": usage or {"input_tokens": 120, "output_tokens": 80},
    }).encode()


class _FakeResponse:
    """Minimal context-manager stand-in for urllib's HTTPResponse."""

    def __init__(self, body: bytes):
        self._body = body
        self.status = 200

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self) -> bytes:
        return self._body


class _FakeStreamResponse:
    """Iterable stand-in for a streaming urllib response."""

    def __init__(self, lines: list[bytes]):
        self._lines = lines
        self.status = 200

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def __iter__(self):
        for line in self._lines:
            yield line


def _sse_chunks(content_chunks: list[str], usage: dict | None = None) -> list[bytes]:
    lines: list[bytes] = []
    for chunk in content_chunks:
        lines.append(b'data: ' + json.dumps({
            "choices": [{"delta": {"content": chunk}}],
        }).encode() + b'\n\n')
    if usage is not None:
        lines.append(b'data: ' + json.dumps({"choices": [{}], "usage": usage}).encode() + b'\n\n')
    lines.append(b'data: [DONE]\n')
    return lines


# ── _call_nvidia contract ──────────────────────────────────────────────────

class TestCallNvidiaContract:
    @patch("engines.ai_insights_engine.urllib.request.urlopen")
    def test_parses_openai_compatible_response(self, mock_urlopen):
        mock_urlopen.return_value = _FakeResponse(_openai_body(VALID_AI_JSON))
        text, usage = ai._call_nvidia("prompt", "nvapi-fake-key-not-real")
        assert parse_ai_response(text).headline == "Discipline held, RTP below expectation"
        assert usage["output_tokens"] == 80

    @patch("engines.ai_insights_engine.urllib.request.urlopen")
    def test_request_carries_bearer_auth_and_json_content_type(self, mock_urlopen):
        mock_urlopen.return_value = _FakeResponse(_openai_body(VALID_AI_JSON))
        ai._call_nvidia("prompt", "nvapi-fake-key-not-real")
        request = mock_urlopen.call_args.args[0]
        assert request.headers.get("Content-type") == "application/json"
        assert request.headers.get("Authorization") == "Bearer nvapi-fake-key-not-real"
        assert request.get_method() == "POST"

    @patch("engines.ai_insights_engine.urllib.request.urlopen")
    def test_http_error_surfaces_as_runtimeerror(self, mock_urlopen):
        import urllib.error
        err = urllib.error.HTTPError(
            "https://integrate.api.nvidia.com", 400, "Bad Request",
            {"Content-Type": "application/json"},
            io.BytesIO(b'{"detail":"bad key"}'),
        )
        mock_urlopen.side_effect = err
        with pytest.raises(RuntimeError, match="NVIDIA API error 400"):
            ai._call_nvidia("prompt", "nvapi-fake-key-not-real")


# ── _stream_nvidia contract ────────────────────────────────────────────────

class TestStreamNvidiaContract:
    @patch("engines.ai_insights_engine.urllib.request.urlopen")
    def test_yields_chunks_then_done_with_usage(self, mock_urlopen):
        mock_urlopen.return_value = _FakeStreamResponse(_sse_chunks(
            ["Hello ", "world"], usage={"input_tokens": 10, "output_tokens": 5}))
        events = list(ai._stream_nvidia("prompt", "nvapi-fake-key-not-real"))
        chunk_events = [e for e in events if e["type"] == "chunk"]
        assert [c["content"] for c in chunk_events] == ["Hello ", "world"]
        done = events[-1]
        assert done["type"] == "done"
        assert done["full_text"] == "Hello world"
        assert done["usage"]["output_tokens"] == 5

    @patch("engines.ai_insights_engine.urllib.request.urlopen")
    def test_http_error_emits_error_event(self, mock_urlopen):
        import urllib.error
        err = urllib.error.HTTPError(
            "https://integrate.api.nvidia.com", 429, "Too Many Requests",
            {"Content-Type": "application/json"},
            io.BytesIO(b'{"detail":"rate limited"}'),
        )
        mock_urlopen.side_effect = err
        events = list(ai._stream_nvidia("prompt", "nvapi-fake-key-not-real"))
        assert events and events[0]["type"] == "error"
        assert "429" in events[0]["error"]


# ── analyse_session_with_ai end-to-end (mocked transport) ───────────────────

@pytest.fixture
def _fake_ai_env(monkeypatch, test_db):
    """Force the engine to believe an API key is configured and Ollama is down.

    Also ensures the ``ai_cost_log`` table exists (V9 schema added in Phase 5;
    ``conftest.py`` only initialises through V7). Without this, the engine's
    silent ``except: pass`` in ``_log_ai_cost`` would mask a real regression in
    cost tracking.
    """
    from database.db import init_db_v9
    init_db_v9()
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-fake-key-not-real")
    monkeypatch.setenv("NVIDIA_MODEL", ai.NVIDIA_MODELS[0])
    monkeypatch.setattr(ai, "is_ollama_available", lambda: False)
    monkeypatch.setattr(ai, "list_available_models", lambda: [])
    # prompt_manager may hit the DB; force no active override so SYSTEM_PROMPT is used.
    monkeypatch.setattr("engines.prompt_manager.get_active_prompt", lambda *_a, **_k: None)
    yield
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_MODEL", raising=False)


@pytest.fixture
def seeded_session(test_db):
    """Insert one session with a couple of events for AI analysis.

    ``owner_id`` is intentionally NULL — these contract tests don't need an
    auth user, and SQLite references sessions(id) on the events FK only.
    """
    import database.db as db
    conn = db.get_connection()
    conn.execute(
        "INSERT INTO sessions (name, game_name, platform, date, duration_minutes, "
        "start_balance, end_balance, net_result, rtp, spins, total_bets, biggest_win, "
        "losing_streak, status) "
        "VALUES ('Test session', 'Slot X', 'desktop', '2026-07-24', 60, 1000, 940, "
        "-60, 91, 100, 500, 25, 8, 'reviewed')"
    )
    conn.execute(
        "INSERT INTO events (session_id, event_type, timestamp, bet_amount, win_amount, "
        "balance_after, confidence_score) "
        "VALUES (1, 'spin', '2026-07-24T10:00:00', 5, 0, 995, 0.9)"
    )
    conn.execute(
        "INSERT INTO events (session_id, event_type, timestamp, bet_amount, win_amount, "
        "balance_after, confidence_score) "
        "VALUES (1, 'spin', '2026-07-24T10:01:00', 5, 25, 1015, 0.92)"
    )
    conn.commit()
    sessions_id = conn.execute("SELECT id FROM sessions").fetchone()["id"]
    conn.close()
    return sessions_id


class TestAnalyseSessionWithAiContract:
    @patch("engines.ai_insights_engine.urllib.request.urlopen")
    def test_full_pipeline_uses_nvidia_source_and_persists(self, mock_urlopen, _fake_ai_env, seeded_session):
        mock_urlopen.return_value = _FakeResponse(_openai_body(VALID_AI_JSON))
        result = ai.analyse_session_with_ai(seeded_session)

        assert result["source"] == "nvidia_ai"
        assert result["ai_available"] is True
        assert result["model"] == ai.NVIDIA_MODELS[0]
        assert result["risk_level"] == "moderate"
        assert result["headline"] == "Discipline held, RTP below expectation"

        # AI insights persisted with the [AI] prefix marker.
        import database.db as db
        conn = db.get_connection()
        rows = conn.execute(
            "SELECT text FROM insights WHERE session_id=? AND text LIKE '[AI]%'",
            (seeded_session,)
        ).fetchall()
        cost_rows = conn.execute(
            "SELECT model, input_tokens, output_tokens, cost_usd FROM ai_cost_log"
        ).fetchall()
        conn.close()
        assert len(rows) == 2
        assert any("RTP 91%" in r["text"] for r in rows)
        assert len(cost_rows) == 1
        assert cost_rows[0]["model"] == ai.NVIDIA_MODELS[0]
        assert cost_rows[0]["input_tokens"] == 120

    @patch("engines.ai_insights_engine.urllib.request.urlopen")
    def test_transport_error_falls_back_to_rule_based(self, mock_urlopen, _fake_ai_env, seeded_session):
        import urllib.error
        mock_urlopen.side_effect = RuntimeError("NVIDIA API error 503")
        result = ai.analyse_session_with_ai(seeded_session)
        # Falls back to rule-based with the error surfaced.
        assert result["source"] == "rule_based"
        assert "ai_error" in result
        assert "503" in result["ai_error"]


class TestRuleBasedFallbackContract:
    def test_no_api_key_falls_back_to_rule_based(self, monkeypatch, test_db, seeded_session):
        # No API key in env or config; Ollama forcibly unavailable.
        monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
        monkeypatch.setattr(ai, "_get_api_key", lambda: None)
        monkeypatch.setattr(ai, "is_ollama_available", lambda: False)
        result = ai.analyse_session_with_ai(seeded_session)
        assert result["source"] == "rule_based"
        assert result["ai_available"] is False
        # risk_level derived from rtp (91%) / losing_streak (8) → high band.
        assert result["risk_level"] in {"moderate", "high", "critical"}


class TestGetAiStatusContract:
    def test_status_reports_key_availability_and_models(self, monkeypatch, test_db):
        monkeypatch.setattr(ai, "_get_api_key", lambda: "nvapi-fake")
        monkeypatch.setattr(ai, "is_ollama_available", lambda: False)
        monkeypatch.setattr(ai, "list_available_models", lambda: [])
        status = ai.get_ai_status()
        assert status["has_api_key"] is True
        assert status["model"] in ai.NVIDIA_MODELS
        assert set(status["available_models"]) == set(ai.NVIDIA_MODELS)
        assert "cost_today" in status
