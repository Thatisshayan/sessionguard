"""
backend/schemas/ai.py
--------------------
Pydantic models for structured AI outputs from Claude.
"""

from __future__ import annotations
import json
import re
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class AiInsightRiskLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class AiInsightSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AiInsightCategory(str, Enum):
    RTP = "rtp"
    BEHAVIOUR = "behaviour"
    DISCIPLINE = "discipline"
    VARIANCE = "variance"
    CONFIDENCE = "confidence"


class AiInsightItem(BaseModel):
    severity: AiInsightSeverity = AiInsightSeverity.INFO
    category: AiInsightCategory = AiInsightCategory.BEHAVIOUR
    text: str = ""


class AiInsightResponse(BaseModel):
    headline: str = "Analysis unavailable"
    risk_level: AiInsightRiskLevel = AiInsightRiskLevel.MODERATE
    insights: list[AiInsightItem] = Field(default_factory=list)
    behaviour_summary: str = ""
    notable_moments: list[str] = Field(default_factory=list)
    discipline_score: int = Field(default=50, ge=0, le=100)
    one_line_verdict: str = ""

    @field_validator("risk_level", mode="before")
    @classmethod
    def normalize_risk_level(cls, v) -> AiInsightRiskLevel:
        try:
            return AiInsightRiskLevel(str(v).lower())
        except ValueError:
            return AiInsightRiskLevel.MODERATE

    @field_validator("discipline_score", mode="before")
    @classmethod
    def clamp_discipline_score(cls, v) -> int:
        try:
            return max(0, min(100, int(v)))
        except (TypeError, ValueError):
            return 50


def parse_ai_response(raw_text: str) -> AiInsightResponse:
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    cleaned = cleaned.strip()

    json_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group())
            return AiInsightResponse.model_validate(data)
        except (json.JSONDecodeError, Exception):
            pass

    return AiInsightResponse(
        headline="Analysis unavailable",
        risk_level=AiInsightRiskLevel.MODERATE,
        insights=[],
        behaviour_summary="Unable to parse AI response",
        notable_moments=[],
        discipline_score=50,
        one_line_verdict="Analysis could not be completed",
    )


def validate_ai_json(raw_text: str) -> dict | None:
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    json_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            return None
    return None


AI_TOOL_SCHEMA = {
    "name": "session_analysis",
    "description": "Structured analysis of a casino/slot session",
    "input_schema": {
        "type": "object",
        "properties": {
            "headline": {"type": "string", "description": "One sentence summary (max 15 words)"},
            "risk_level": {"type": "string", "enum": ["low", "moderate", "high", "critical"]},
            "insights": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "string", "enum": ["info", "warning", "critical"]},
                        "category": {"type": "string", "enum": ["rtp", "behaviour", "discipline", "variance", "confidence"]},
                        "text": {"type": "string"},
                    },
                    "required": ["severity", "category", "text"],
                },
            },
            "behaviour_summary": {"type": "string"},
            "notable_moments": {"type": "array", "items": {"type": "string"}},
            "discipline_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "one_line_verdict": {"type": "string"},
        },
        "required": ["headline", "risk_level", "insights", "behaviour_summary", "discipline_score", "one_line_verdict"],
    },
}