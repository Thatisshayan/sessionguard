"""Targeted coverage bump for ai_insights_engine.py (Revival 1.3, Track B).
Covers edge cases not hit by the contract tests.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines import ai_insights_engine as ai


@pytest.fixture
def seeded_session(test_db):
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


# ── _get_model / _get_api_key config fallbacks ────────────────────────────────

class TestGetModelKeyConfigFallbacks:
    def test_get_model_uses_env_var(self, monkeypatch):
        monkeypatch.setenv("NVIDIA_MODEL", "nvidia/mistral-large-2-instruct")
        assert ai._get_model() == "nvidia/mistral-large-2-instruct"

    def test_get_model_falls_back_to_config(self, monkeypatch, tmp_path):
        monkeypatch.delenv("NVIDIA_MODEL", raising=False)
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps({"ai": {"nvidia_model": "nvidia/mistral-large-2-instruct"}}))
        monkeypatch.setattr(ai, "_CONFIG_PATH", cfg_file)
        assert ai._get_model() == "nvidia/mistral-large-2-instruct"

    def test_get_model_returns_default_on_config_error(self, monkeypatch):
        monkeypatch.delenv("NVIDIA_MODEL", raising=False)
        monkeypatch.setattr(ai, "_CONFIG_PATH", Path("/nonexistent/config.json"))
        assert ai._get_model() == ai.NVIDIA_MODELS[0]

    def test_get_api_key_uses_env(self, monkeypatch):
        monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-env-key")
        assert ai._get_api_key() == "nvapi-env-key"

    def test_get_api_key_falls_back_to_config(self, monkeypatch, tmp_path):
        monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps({"ai": {"nvidia_api_key": "nvapi-config-key"}}))
        monkeypatch.setattr(ai, "_CONFIG_PATH", cfg_file)
        assert ai._get_api_key() == "nvapi-config-key"

    def test_get_api_key_returns_none_on_config_error(self, monkeypatch):
        monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
        monkeypatch.setattr(ai, "_CONFIG_PATH", Path("/nonexistent/config.json"))
        assert ai._get_api_key() is None

    def test_is_available_delegates(self, monkeypatch):
        monkeypatch.setattr(ai, "_get_api_key", lambda: "key")
        assert ai.is_available() is True
        monkeypatch.setattr(ai, "_get_api_key", lambda: None)
        assert ai.is_available() is False


# ── _build_session_summary edge cases ─────────────────────────────────────────

class TestBuildSessionSummary:
    def test_returns_none_for_missing_session(self, test_db):
        assert ai._build_session_summary(99999) is None

    def test_handles_small_balance_curve(self, test_db):
        import database.db as db
        conn = db.get_connection()
        conn.execute(
            "INSERT INTO sessions (name, game_name, platform, date, start_balance, end_balance, status) "
            "VALUES ('s', 'g', 'desktop', '2026-07-24', 1000, 940, 'reviewed')"
        )
        conn.execute(
            "INSERT INTO events (session_id, event_type, timestamp, bet_amount, win_amount, balance_after, confidence_score) "
            "VALUES (1, 'spin', '2026-07-24T10:00:00', 5, 0, 995, 0.9)"
        )
        conn.execute(
            "INSERT INTO events (session_id, event_type, timestamp, bet_amount, win_amount, balance_after, confidence_score) "
            "VALUES (1, 'spin', '2026-07-24T10:01:00', 5, 25, 1015, 0.92)"
        )
        conn.commit()
        conn.close()
        summary = ai._build_session_summary(1)
        assert summary is not None
        assert len(summary["balance_curve"]) == 2


# ── analyse_session_with_ai fallbacks ─────────────────────────────────────────

class TestAnalyseWithAiFallbacks:
    def test_returns_error_for_missing_session(self, test_db):
        result = ai.analyse_session_with_ai(99999)
        assert "error" in result
        assert "not found" in result["error"]

    def test_ollama_fallback_path(self, monkeypatch, test_db, seeded_session):
        monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
        monkeypatch.setattr(ai, "_get_api_key", lambda: None)
        monkeypatch.setattr(ai, "is_ollama_available", lambda: True)
        monkeypatch.setattr(ai, "_is_budget_exceeded_unsafe", lambda: False)
        monkeypatch.setattr(ai, "list_available_models", lambda: ["llama3.2"])

        def _fake_ollama_call(prompt, **_kw):
            return {"headline": "Ollama analysis", "risk_level": "low",
                    "insights": [{"severity": "info", "category": "behaviour",
                                  "text": "Ollama test insight"}],
                    "behaviour_summary": "OK", "discipline_score": 80,
                    "one_line_verdict": "All good"}

        monkeypatch.setattr(ai, "call_ollama_json", _fake_ollama_call)
        monkeypatch.setattr("engines.prompt_manager.get_active_prompt", lambda *_a, **_k: None)

        result = ai.analyse_session_with_ai(seeded_session)
        assert result["source"] == "ollama_ai"

    def test_ollama_error_falls_to_rule_based(self, monkeypatch, test_db, seeded_session):
        monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
        monkeypatch.setattr(ai, "_get_api_key", lambda: None)
        monkeypatch.setattr(ai, "is_ollama_available", lambda: True)
        monkeypatch.setattr(ai, "_is_budget_exceeded_unsafe", lambda: False)

        def _fake_ollama_call(prompt, **_kw):
            return {"error": "model not loaded"}

        monkeypatch.setattr(ai, "call_ollama_json", _fake_ollama_call)
        monkeypatch.setattr("engines.prompt_manager.get_active_prompt", lambda *_a, **_k: None)

        result = ai.analyse_session_with_ai(seeded_session)
        assert result["source"] == "rule_based"


# ── Budget helpers ────────────────────────────────────────────────────────────

class TestBudget:
    def test_is_budget_exceeded_unsafe_db_error(self, monkeypatch):
        monkeypatch.setenv("SG_AI_BUDGET_USD", "10.0")
        monkeypatch.setattr(ai, "get_connection", lambda: (_ for _ in ()).throw(Exception("db error")))
        assert ai._is_budget_exceeded_unsafe() is False

    def test_get_config_budget_default_on_error(self, monkeypatch):
        monkeypatch.setattr(ai, "_CONFIG_PATH", Path("/nonexistent/config.json"))
        assert ai._get_config_budget() == "10.0"

    def test_get_daily_cost_db_error(self, monkeypatch):
        monkeypatch.setattr(ai, "get_connection", lambda: (_ for _ in ()).throw(Exception("db error")))
        result = ai.get_daily_cost()
        assert result["calls_today"] == 0
        assert result["cost_usd"] == 0

    def test_is_budget_exceeded_delegates(self, monkeypatch):
        monkeypatch.setattr(ai, "get_daily_cost", lambda: {"budget_exceeded": True})
        assert ai.is_budget_exceeded() is True

        monkeypatch.setattr(ai, "get_daily_cost", lambda: {"budget_exceeded": False})
        assert ai.is_budget_exceeded() is False

    def test_get_daily_cost_returns_data(self, monkeypatch, test_db):
        from database.db import init_db_v9
        init_db_v9()
        import database.db as db
        conn = db.get_connection()
        conn.execute(
            "INSERT INTO ai_cost_log (session_id, model, input_tokens, output_tokens, cost_usd) "
            "VALUES (1, 'test-model', 100, 50, 0.001)"
        )
        conn.commit()
        conn.close()
        monkeypatch.setenv("SG_AI_BUDGET_USD", "10.0")
        result = ai.get_daily_cost()
        assert result["calls_today"] == 1
        assert result["cost_usd"] == 0.001
        assert result["remaining_usd"] == 9.999


# ── _persist_ai_insights edge case ────────────────────────────────────────────

class TestPersistAiInsights:
    def test_noop_when_no_insights(self, test_db):
        ai._persist_ai_insights(1, {"source": "nvidia_ai"})
        import database.db as db
        conn = db.get_connection()
        count = conn.execute("SELECT COUNT(*) FROM insights").fetchone()[0]
        conn.close()
        assert count == 0


# ── stream_analyse_session ────────────────────────────────────────────────────

class TestStreamAnalyse:
    def test_session_not_found(self, test_db):
        events = list(ai.stream_analyse_session(99999))
        assert events and events[0]["type"] == "error"
        assert "not found" in events[0]["error"]

    def test_no_api_key_returns_rule_based(self, monkeypatch, test_db, seeded_session):
        monkeypatch.setattr(ai, "_get_api_key", lambda: None)
        monkeypatch.setattr(ai, "is_ollama_available", lambda: False)
        events = list(ai.stream_analyse_session(seeded_session))
        assert events and events[0]["type"] == "done"
        assert events[0]["analysis"]["source"] == "rule_based"


# ── set_model ─────────────────────────────────────────────────────────────────

class TestSetModel:
    def test_unknown_model_returns_error(self):
        result = ai.set_model("nonexistent-model")
        assert "error" in result

    def test_config_write_error_does_not_block(self, monkeypatch):
        monkeypatch.setattr(ai, "_CONFIG_PATH", Path("/nonexistent/readonly/config.json"))
        result = ai.set_model(ai.NVIDIA_MODELS[0])
        assert result["model"] == ai.NVIDIA_MODELS[0]


# ── generate_comparison_narrative ─────────────────────────────────────────────

class TestComparisonNarrative:
    def test_single_session_error(self, test_db):
        import database.db as db
        conn = db.get_connection()
        conn.execute(
            "INSERT INTO sessions (name, game_name, platform, date, start_balance, end_balance, status) "
            "VALUES ('s1', 'g1', 'desktop', '2026-07-24', 1000, 940, 'reviewed')"
        )
        conn.commit()
        conn.close()
        result = ai.generate_comparison_narrative([1])
        assert "error" in result
        assert "at least 2" in result["error"]

    def test_rule_based_fallback(self, monkeypatch, test_db):
        import database.db as db
        conn = db.get_connection()
        conn.execute(
            "INSERT INTO sessions (name, game_name, platform, date, start_balance, end_balance, net_result, rtp, spins, status) "
            "VALUES ('s1', 'g1', 'desktop', '2026-07-24', 1000, 940, -60, 91, 100, 'reviewed')"
        )
        conn.execute(
            "INSERT INTO sessions (name, game_name, platform, date, start_balance, end_balance, net_result, rtp, spins, status) "
            "VALUES ('s2', 'g2', 'desktop', '2026-07-25', 500, 520, 20, 98, 50, 'reviewed')"
        )
        conn.commit()
        conn.close()
        monkeypatch.setattr(ai, "_get_api_key", lambda: None)
        result = ai.generate_comparison_narrative([1, 2])
        assert result["source"] == "rule_based"
        assert "Compared 2 sessions" in result["content"]


# ── suggest_review_resolution ─────────────────────────────────────────────────

class TestSuggestReviewResolution:
    def test_missing_item(self, test_db):
        result = ai.suggest_review_resolution(99999)
        assert "error" in result
        assert "not found" in result["error"]

    @pytest.mark.parametrize("conf,suggestion", [(0.95, "accept"), (0.72, "accept"), (0.45, "reject")])
    def test_confidence_thresholds(self, test_db, conf, suggestion):
        import database.db as db
        conn = db.get_connection()
        conn.execute(
            "INSERT INTO sessions (name, game_name, platform, date, start_balance, end_balance, status) "
            "VALUES ('s', 'g', 'desktop', '2026-07-24', 1000, 940, 'reviewed')"
        )
        conn.execute(
            "INSERT INTO events (session_id, event_type, timestamp, bet_amount, win_amount, balance_after, confidence_score) "
            "VALUES (1, 'spin', '2026-07-24T10:00:00', 5, 0, 995, ?)", (conf,)
        )
        conn.execute(
            "INSERT INTO review_items (session_id, event_id, reason, status) "
            "VALUES (1, 1, 'test', 'pending')"
        )
        conn.commit()
        review_id = conn.execute("SELECT id FROM review_items").fetchone()["id"]
        conn.close()
        result = ai.suggest_review_resolution(review_id)
        assert result["suggestion"] == suggestion
