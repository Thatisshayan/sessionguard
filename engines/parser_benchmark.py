"""
engines/parser_benchmark.py
-----------------------------
Tests OCR accuracy of a profile's ROI config against a set of reference frames.

Purpose: Help users calibrate their ROI coordinates by running OCR over
         sample frames and comparing against known ground-truth values.

Maturity: Working Prototype
Future:   Auto-calibration using ML (V10), web-based coordinate picker UI (V9).
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Optional

from database.db import get_connection
from engines.ocr_engine import extract_fields_from_image, scan_image


def run_benchmark(
    frame_paths:    list[str],
    roi_config:     dict | None = None,
    ground_truth:   list[dict] | None = None,
) -> dict:
    """
    Run OCR over a list of frames using the given ROI config.
    Optionally compare against ground truth values.

    ground_truth format:
        [{"balance": 523.50, "bet": 2.00, "win": 0.00}, ...]
        One entry per frame. Use None for unknown fields.

    Returns:
        per-frame results, aggregate confidence stats, accuracy metrics.
    """
    results      = []
    confidences  : list[float] = []
    errors       : list[float] = []

    for i, frame_path in enumerate(frame_paths):
        frame = Path(frame_path)
        if not frame.exists():
            results.append({
                "frame":  frame_path,
                "error":  "File not found",
                "fields": {},
            })
            continue

        ocr_result = extract_fields_from_image(str(frame), roi_config=roi_config)
        fields     = ocr_result.get("fields", {})
        conf_avg   = ocr_result.get("overall_confidence", 0.0)
        confidences.append(conf_avg)

        frame_result = {
            "frame":             frame_path,
            "overall_confidence": conf_avg,
            "flagged":           ocr_result.get("flagged", False),
            "fields":            fields,
        }

        # Compare against ground truth if provided
        if ground_truth and i < len(ground_truth):
            gt     = ground_truth[i] or {}
            deltas = {}
            for field_name in ("balance", "bet", "win"):
                detected_val = fields.get(field_name, {}).get("value")
                expected_val = gt.get(field_name)
                if expected_val is not None and detected_val is not None:
                    delta = abs(detected_val - expected_val)
                    deltas[field_name] = {
                        "expected": expected_val,
                        "detected": detected_val,
                        "delta":    round(delta, 2),
                        "accurate": delta < 1.0,  # within $1
                    }
                    errors.append(delta)
                elif expected_val is not None:
                    deltas[field_name] = {
                        "expected": expected_val,
                        "detected": None,
                        "delta":    None,
                        "accurate": False,
                    }
            frame_result["ground_truth_comparison"] = deltas

        results.append(frame_result)

    # Aggregate stats
    avg_confidence = round(sum(confidences) / len(confidences), 3) if confidences else 0.0
    avg_error      = round(sum(errors)      / len(errors),      2)  if errors      else None
    accuracy_pct   = round(
        sum(1 for e in errors if e < 1.0) / len(errors) * 100, 1
    ) if errors else None

    low_conf_count = sum(1 for c in confidences if c < 0.75)
    flagged_count  = sum(1 for r in results if r.get("flagged"))

    return {
        "frame_count":      len(frame_paths),
        "processed":        len(results),
        "avg_confidence":   avg_confidence,
        "low_conf_count":   low_conf_count,
        "flagged_count":    flagged_count,
        "avg_error_dollars": avg_error,
        "accuracy_pct":     accuracy_pct,
        "has_ground_truth": bool(ground_truth),
        "recommendation":   _build_recommendation(avg_confidence, low_conf_count, len(frame_paths)),
        "results":          results,
    }


def _build_recommendation(avg_conf: float, low_conf_count: int, total: int) -> str:
    if avg_conf >= 0.90:
        return "ROI config is well-calibrated. OCR confidence is high."
    if avg_conf >= 0.75:
        return (
            f"{low_conf_count}/{total} frames had low confidence. "
            "Try increasing the scale factor or adjusting ROI boundaries slightly."
        )
    return (
        f"Average confidence of {avg_conf:.0%} is too low. "
        "ROI regions likely need recalibration. "
        "Check that coordinates target the correct screen regions and that "
        "scale is set to at least 2.0."
    )


def benchmark_profile(profile_id: int, frame_paths: list[str]) -> dict:
    """
    Run benchmark using a stored profile's ROI config.
    """
    conn = get_connection()
    profile = conn.execute("SELECT * FROM profiles WHERE id=?", (profile_id,)).fetchone()
    conn.close()
    if not profile:
        return {"error": f"Profile {profile_id} not found."}

    try:
        roi_config = json.loads(profile["roi_config"] or "{}")
    except Exception:
        roi_config = {}

    result = run_benchmark(frame_paths, roi_config=roi_config)
    result["profile_id"]   = profile_id
    result["profile_name"] = profile["name"]
    result["roi_config"]   = roi_config
    return result
