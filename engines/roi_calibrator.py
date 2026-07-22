"""
engines/roi_calibrator.py
--------------------------
Automatic ROI (region-of-interest) calibration from a single screenshot.

Takes a game screenshot, detects text regions via contour analysis,
identifies balance/bet/win fields by OCRing nearby labels, and returns
a ready-to-use roi_config dict.

Maturity: Working Prototype — contour-based detection with OCR label matching.
"""

from __future__ import annotations
import re
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from engines.ocr_engine import preprocess_image, scan_image


# ── Constants ─────────────────────────────────────────────────────────────────

# Contour filtering
MIN_CONTOUR_AREA = 200     # ignore tiny noise
MAX_CONTOUR_AREA = 50000   # ignore full-screen blobs
ASPECT_RATIO_MIN = 1.5     # numeric fields are wider than tall
ASPECT_RATIO_MAX = 12.0

# Label matching
FIELD_LABELS = {
    "balance": ["balance", "bal", "credit", "credits", "total", "cash"],
    "bet":     ["bet", "wager", "stake", "total bet", "bet amount"],
    "win":     ["win", "winning", "payout", "prize", "won"],
}

# Numeric pattern for validation
NUMERIC_RE = re.compile(r"[\d,.]+(?:\.\d+)?")


# ── Contour detection ────────────────────────────────────────────────────────

def _find_text_regions(image_path: str) -> list[dict]:
    """
    Detect rectangular text regions in a screenshot using contour analysis.
    Returns list of {x, y, w, h, area, aspect_ratio} sorted top-to-bottom.
    """
    img = cv2.imread(image_path)
    if img is None:
        return []

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Adaptive threshold to handle varying background colors
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 15, 8
    )

    # Dilate to connect nearby text characters into regions
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3))
    dilated = cv2.dilate(binary, kernel, iterations=2)

    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    regions = []
    h_img, w_img = img.shape[:2]

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h
        aspect = w / max(h, 1)

        if area < MIN_CONTOUR_AREA or area > MAX_CONTOUR_AREA:
            continue
        if aspect < ASPECT_RATIO_MIN or aspect > ASPECT_RATIO_MAX:
            continue
        # Skip regions that span most of the image width (likely backgrounds)
        if w > w_img * 0.8:
            continue
        # Skip regions at very top/bottom 5% (likely UI chrome)
        if y < h_img * 0.05 or y + h > h_img * 0.95:
            continue

        regions.append({
            "x": x, "y": y, "w": w, "h": h,
            "area": area,
            "aspect_ratio": round(aspect, 2),
            "cx": x + w // 2,  # center x
            "cy": y + h // 2,  # center y
        })

    # Sort top-to-bottom, then left-to-right
    regions.sort(key=lambda r: (r["cy"], r["cx"]))
    return regions


def _label_for_region(image_path: str, region: dict, margin: int = 80) -> str | None:
    """
    Look for a text label to the left of (or above) a detected region.
    OCRs the label area and checks against known field labels.
    """
    img = Image.open(image_path)
    w_img, h_img = img.size
    x, y, w, h = region["x"], region["y"], region["w"], region["h"]

    # Check area to the left of the region
    label_x = max(0, x - margin)
    label_y = max(0, y - h // 2)
    label_w = min(margin, x)
    label_h = h * 2

    if label_w > 10 and label_h > 10:
        label_crop = img.crop((label_x, label_y, label_x + label_w, label_y + label_h))
        label_text = _ocr_label_image(label_crop).lower()
        for field, keywords in FIELD_LABELS.items():
            for kw in keywords:
                if kw in label_text:
                    return field

    # Check area above the region
    label_x2 = max(0, x - w // 4)
    label_y2 = max(0, y - margin)
    label_w2 = w + w // 2
    label_h2 = min(margin, y)

    if label_w2 > 10 and label_h2 > 10:
        label_crop2 = img.crop((label_x2, label_y2, label_x2 + label_w2, label_y2 + label_h2))
        label_text2 = _ocr_label_image(label_crop2).lower()
        for field, keywords in FIELD_LABELS.items():
            for kw in keywords:
                if kw in label_text2:
                    return field

    return None


def _ocr_label_image(img: Image.Image) -> str:
    """Quick OCR on a small label crop. Returns extracted text."""
    processed = preprocess_image(img, scale=2.0, sharpen=True)
    try:
        import pytesseract
        text = pytesseract.image_to_string(processed, config="--psm 7 --oem 3")
        return text.strip()
    except Exception:
        return ""


def _region_has_numeric(image_path: str, region: dict) -> bool:
    """Check if a region contains numeric data (likely a value field)."""
    img = Image.open(image_path)
    crop = img.crop((region["x"], region["y"],
                     region["x"] + region["w"], region["y"] + region["h"]))
    processed = preprocess_image(crop, scale=2.0)
    try:
        import pytesseract
        text = pytesseract.image_to_string(processed, config="--psm 7 --oem 3")
        return bool(NUMERIC_RE.search(text))
    except Exception:
        return False


# ── Public API ────────────────────────────────────────────────────────────────

def auto_calibrate_roi(image_path: str) -> dict:
    """
    Analyze a game screenshot and auto-detect ROI regions for balance/bet/win.

    Returns:
        {
            "success": bool,
            "roi_config": { "balance_region": [...], "bet_region": [...], ... },
            "detected_regions": [...],
            "labels_found": { "balance": bool, "bet": bool, "win": bool },
            "confidence": float,  # 0-1, how many fields were labeled
            "message": str,
        }
    """
    path = Path(image_path)
    if not path.exists():
        return {"success": False, "error": f"File not found: {image_path}", "roi_config": {}}

    regions = _find_text_regions(image_path)
    if not regions:
        return {
            "success": False,
            "error": "No text regions detected. Try a clearer screenshot.",
            "roi_config": {},
            "detected_regions": [],
        }

    # Label each region
    labeled = {}
    for region in regions:
        label = _label_for_region(image_path, region)
        if label and label not in labeled:
            # Verify the region actually contains numeric data
            if _region_has_numeric(image_path, region):
                labeled[label] = region

    # Build ROI config from labeled regions
    roi_config = {}
    fields_found = {}

    for field in ["balance", "bet", "win"]:
        if field in labeled:
            r = labeled[field]
            roi_config[f"{field}_region"] = [r["x"], r["y"], r["w"], r["h"]]
            fields_found[field] = True
        else:
            fields_found[field] = False

    confidence = sum(fields_found.values()) / 3.0

    if confidence == 0:
        # Fallback: assume top region = balance, middle = bet, bottom = win
        # based on common slot machine UI layout
        if len(regions) >= 3:
            # Take the 3 most numeric-looking regions
            numeric_regions = [(r, _region_has_numeric(image_path, r)) for r in regions[:10]]
            value_regions = [r for r, is_num in numeric_regions if is_num][:3]

            if len(value_regions) >= 3:
                roi_config = {
                    "balance_region": [value_regions[0]["x"], value_regions[0]["y"],
                                       value_regions[0]["w"], value_regions[0]["h"]],
                    "bet_region":     [value_regions[1]["x"], value_regions[1]["y"],
                                       value_regions[1]["w"], value_regions[1]["h"]],
                    "win_region":     [value_regions[2]["x"], value_regions[2]["y"],
                                       value_regions[2]["w"], value_regions[2]["h"]],
                }
                fields_found = {"balance": True, "bet": True, "win": True}
                confidence = 0.5  # lower confidence for positional guess

    message = _build_message(fields_found, confidence, len(regions))

    return {
        "success":          confidence > 0,
        "roi_config":       roi_config,
        "detected_regions": regions[:20],  # cap for response size
        "labels_found":     fields_found,
        "confidence":       confidence,
        "message":          message,
    }


def _build_message(fields_found: dict, confidence: float, region_count: int) -> str:
    """Build a human-readable summary message."""
    found = [k for k, v in fields_found.items() if v]
    missing = [k for k, v in fields_found.items() if not v]

    parts = [f"Detected {region_count} text regions."]
    if found:
        parts.append(f"Identified: {', '.join(found)}.")
    if missing:
        parts.append(f"Missing: {', '.join(missing)}.")
    if confidence >= 0.9:
        parts.append("ROI config ready — high confidence.")
    elif confidence >= 0.5:
        parts.append("ROI config generated — verify regions manually.")
    else:
        parts.append("Low confidence — manual calibration recommended.")

    return " ".join(parts)
