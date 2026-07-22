import pytest
from backend.schemas.ai import (
    AiInsightResponse, AiInsightRiskLevel,
    AiInsightItem, parse_ai_response, validate_ai_json,
)


class TestAiInsightResponse:
    def test_valid_response_parsing(self):
        raw = {
            "headline": "Session showed escalation pattern",
            "risk_level": "high",
            "insights": [
                {"severity": "warning", "category": "behaviour", "text": "Bet size doubled"}
            ],
            "behaviour_summary": "Player escalated bets late in session",
            "notable_moments": ["Bet increased from $10 to $25 at spin 50"],
            "discipline_score": 45,
            "one_line_verdict": "Escalation detected — consider setting limits"
        }
        result = AiInsightResponse.model_validate(raw)
        assert result.risk_level == AiInsightRiskLevel.HIGH
        assert len(result.insights) == 1
        assert result.discipline_score == 45

    def test_invalid_risk_level_fallback(self):
        raw = {
            "headline": "Test", "risk_level": "INVALID", "insights": [],
            "behaviour_summary": "Test", "notable_moments": [],
            "discipline_score": 50, "one_line_verdict": "Test"
        }
        result = AiInsightResponse.model_validate(raw)
        assert result.risk_level == AiInsightRiskLevel.MODERATE

    def test_missing_fields_use_defaults(self):
        raw = {"headline": "Test"}
        result = AiInsightResponse.model_validate(raw)
        assert result.risk_level == AiInsightRiskLevel.MODERATE
        assert result.insights == []
        assert result.discipline_score == 50


class TestParseAiResponse:
    def test_strips_markdown_fences(self):
        raw = '```json\n{"headline": "Test", "risk_level": "low", "insights": [], "behaviour_summary": "", "notable_moments": [], "discipline_score": 70, "one_line_verdict": "Good"}\n```'
        result = parse_ai_response(raw)
        assert result.headline == "Test"

    def test_handles_plain_json(self):
        raw = '{"headline": "Test", "risk_level": "low", "insights": [], "behaviour_summary": "", "notable_moments": [], "discipline_score": 70, "one_line_verdict": "Good"}'
        result = parse_ai_response(raw)
        assert result.headline == "Test"

    def test_returns_fallback_on_invalid(self):
        result = parse_ai_response("not json at all")
        assert result.headline == "Analysis unavailable"
        assert result.risk_level == AiInsightRiskLevel.MODERATE