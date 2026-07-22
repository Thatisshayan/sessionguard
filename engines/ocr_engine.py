"""
engines/ocr_engine.py
----------------------
Real OCR pipeline using Tesseract 5.x via pytesseract.

Capabilities:
  - Full image scan with word-level confidence scores
  - ROI (region-of-interest) crop per profile config
  - Image preprocessing: grayscale, threshold, scale, denoise
  - Field extraction: balance, bet, win (numeric parsing with confidence)
  - Low-confidence flagging for review queue
  - Results persisted to ocr_results table

Maturity: Working Prototype — real OCR, real confidence, real field extraction.
Future:   EasyOCR fallback (V7), GPU acceleration (V10).
"""

from __future__ import annotations
import re
import shutil
from pathlib import Path
from typing import Optional

from PIL import Image, ImageFilter, ImageEnhance
import pytesseract

from database.db import get_connection

# ── Windows: hard-set Tesseract path so pytesseract never guesses ─────────────
import os, platform
if platform.system() == "Windows":
    _tess_exe = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    _tess_data = r"C:\Program Files\Tesseract-OCR\tessdata"
    if os.path.exists(_tess_exe):
        pytesseract.pytesseract.tesseract_cmd = _tess_exe
    if os.path.exists(_tess_data):
        os.environ["TESSDATA_PREFIX"] = _tess_data

# ── Constants ─────────────────────────────────────────────────────────────────
CONFIDENCE_THRESHOLD = 0.75   # below this → flagged for review
NUMERIC_PATTERN = re.compile(r"[-+]?\d{1,6}(?:[.,]\d{1,2})?")


# ── Availability check ────────────────────────────────────────────────────────

def check_ocr_status() -> dict:
    """Return honest status of all OCR backends."""
    tesseract_path = shutil.which("tesseract")
    tess_ok = False
    tess_version = None

    if tesseract_path:
        try:
            import subprocess
            r = subprocess.run(
                ["tesseract", "--version"],
                capture_output=True, text=True, timeout=5
            )
            tess_version = r.stdout.splitlines()[0] if r.stdout else r.stderr.splitlines()[0]
            tess_ok = True
        except Exception:
            pass

    try:
        import easyocr  # noqa: F401
        easy_ok = True
    except ImportError:
        easy_ok = False

    any_available = tess_ok or easy_ok
    return {
        "any_available": any_available,
        "backends": {
            "tesseract": {
                "available": tess_ok,
                "path":      tesseract_path,
                "version":   tess_version,
            },
            "easyocr": {
                "available": easy_ok,
                "install":   None if easy_ok else "pip install easyocr",
            },
        },
        "message": (
            f"Tesseract {tess_version} ready." if tess_ok
            else "No OCR backend available. Install Tesseract: https://github.com/tesseract-ocr/tesseract"
        ),
    }


# ── Image preprocessing ───────────────────────────────────────────────────────

def preprocess_image(
    image: Image.Image,
    scale: float = 2.0,
    sharpen: bool = True,
    threshold: Optional[int] = None,
) -> Image.Image:
    """
    Prepare an image for OCR:
    1. Convert to grayscale
    2. Scale up (2x default — improves Tesseract accuracy significantly)
    3. Sharpen
    4. Optional binarisation threshold
    """
    img = image.convert("L")  # grayscale

    # Scale up — critical for small UI text
    new_w = int(img.width  * scale)
    new_h = int(img.height * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)

    if sharpen:
        img = img.filter(ImageFilter.SHARPEN)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)

    if threshold is not None:
        img = img.point(lambda p: 255 if p > threshold else 0)

    return img


def crop_roi(image: Image.Image, roi: list[int]) -> Image.Image:
    """
    Crop image to region of interest.
    roi = [x, y, width, height]
    """
    x, y, w, h = roi
    return image.crop((x, y, x + w, y + h))


# ── Core scan ─────────────────────────────────────────────────────────────────

def scan_image(file_path: str) -> dict:
    """
    Full-image OCR scan.
    Returns: words list with bounding boxes + confidence, extracted text,
             and confidence_average.
    """
    try:
        image = Image.open(file_path)
    except Exception as e:
        return {"error": str(e), "text": "", "confidence_average": None, "words": []}

    processed = preprocess_image(image)
    data = pytesseract.image_to_data(
        processed,
        output_type=pytesseract.Output.DICT,
        config="--psm 6 --oem 3",   # psm 6 = uniform block of text
    )

    words = []
    confidences = []

    for i, text in enumerate(data.get("text", [])):
        stripped = (text or "").strip()
        if not stripped:
            continue
        conf_raw = data.get("conf", [])[i]
        try:
            conf = float(conf_raw)
        except Exception:
            conf = -1.0

        if conf >= 0:
            confidences.append(conf / 100.0)  # normalise to 0-1

        words.append({
            "text":       stripped,
            "confidence": round(conf / 100.0, 3) if conf >= 0 else -1,
            "left":       int(data["left"][i]),
            "top":        int(data["top"][i]),
            "width":      int(data["width"][i]),
            "height":     int(data["height"][i]),
        })

    extracted_text = " ".join(w["text"] for w in words)
    confidence_avg = round(sum(confidences) / len(confidences), 3) if confidences else None

    return {
        "source_path":        str(Path(file_path)),
        "text":               extracted_text,
        "confidence_average": confidence_avg,
        "words":              words,
        "word_count":         len(words),
    }


# ── EasyOCR fallback ─────────────────────────────────────────────────────────

_easyocr_reader = None

def _get_easyocr_reader():
    """Lazy-load EasyOCR reader (GPU if available, else CPU)."""
    global _easyocr_reader
    if _easyocr_reader is None:
        import easyocr
        _easyocr_reader = easyocr.Reader(
            ["en"],
            gpu=False,  # safe default; set True via env EASYOCR_GPU=1
        )
    return _easyocr_reader


def scan_with_easyocr(file_path: str) -> dict:
    """
    OCR scan using EasyOCR (fallback for low-confidence Tesseract results).
    Returns same format as scan_image for compatibility.
    """
    try:
        reader = _get_easyocr_reader()
    except ImportError:
        return {"error": "EasyOCR not installed. pip install easyocr", "text": "",
                "confidence_average": None, "words": []}
    except Exception as e:
        return {"error": f"EasyOCR init failed: {e}", "text": "",
                "confidence_average": None, "words": []}

    try:
        results = reader.readtext(file_path)
    except Exception as e:
        return {"error": f"EasyOCR read failed: {e}", "text": "",
                "confidence_average": None, "words": []}

    words = []
    confidences = []
    for (bbox, text, conf) in results:
        if not text.strip():
            continue
        # bbox is [[x1,y1],[x2,y2],[x3,y3],[x4,y4]] — compute bounding rect
        xs = [p[0] for p in bbox]
        ys = [p[1] for p in bbox]
        x1, y1 = int(min(xs)), int(min(ys))
        w, h = int(max(xs) - x1), int(max(ys) - y1)

        c = float(conf)
        confidences.append(c)
        words.append({
            "text":       text.strip(),
            "confidence": round(c, 3),
            "left":       x1,
            "top":        y1,
            "width":      w,
            "height":     h,
        })

    extracted_text = " ".join(w["text"] for w in words)
    confidence_avg = round(sum(confidences) / len(confidences), 3) if confidences else None

    return {
        "source_path":        str(Path(file_path)),
        "text":               extracted_text,
        "confidence_average": confidence_avg,
        "words":              words,
        "word_count":         len(words),
        "backend":            "easyocr",
    }


# ── Field extraction ──────────────────────────────────────────────────────────

def _extract_numeric(words: list[dict], region_words: list[dict] | None = None) -> tuple[float | None, float]:
    """
    Find the most likely numeric value in a list of OCR words.
    Returns (value, confidence) or (None, 0.0).
    """
    target = region_words if region_words is not None else words
    best_value = None
    best_conf  = 0.0

    for w in target:
        text  = w["text"].replace(",", ".")
        match = NUMERIC_PATTERN.search(text)
        if match:
            try:
                val  = float(match.group())
                conf = w["confidence"] if w["confidence"] >= 0 else 0.0
                if conf > best_conf or best_value is None:
                    best_value = val
                    best_conf  = conf
            except ValueError:
                continue

    return best_value, round(best_conf, 3)


def extract_fields_from_image(
    file_path: str,
    roi_config: dict | None = None,
) -> dict:
    """
    Extract balance, bet, win fields from a game screenshot.
    Automatically falls back to EasyOCR when Tesseract confidence < 0.75.

    roi_config format (from profile):
        {
            "balance_region": [x, y, width, height],
            "bet_region":     [x, y, width, height],
            "win_region":     [x, y, width, height],
            "scale":          2.0,
            "threshold":      128,
        }

    Returns per-field (value, confidence) + flagged status.
    """
    try:
        image = Image.open(file_path)
    except Exception as e:
        return {"error": str(e), "fields": {}}

    scale     = float((roi_config or {}).get("scale", 2.0))
    threshold = (roi_config or {}).get("threshold", None)

    fields    = {}
    flag      = False
    field_defs = {
        "balance": "balance_region",
        "bet":     "bet_region",
        "win":     "win_region",
    }

    # Check if EasyOCR is available for fallback
    try:
        import easyocr
        easyocr_available = True
    except ImportError:
        easyocr_available = False

    for field_name, roi_key in field_defs.items():
        roi = (roi_config or {}).get(roi_key)
        if roi:
            cropped   = crop_roi(image, roi)
            processed = preprocess_image(cropped, scale=scale, threshold=threshold)
            # Save cropped region for EasyOCR fallback
            crop_path = file_path
        else:
            processed = preprocess_image(image, scale=scale, threshold=threshold)
            crop_path = file_path

        # Tesseract pass
        data = pytesseract.image_to_data(
            processed,
            output_type=pytesseract.Output.DICT,
            config="--psm 7 --oem 3",   # psm 7 = single line
        )

        words = []
        for i, text in enumerate(data.get("text", [])):
            stripped = (text or "").strip()
            if not stripped:
                continue
            conf_raw = data.get("conf", [])[i]
            try:
                conf = float(conf_raw) / 100.0
            except Exception:
                conf = -1.0
            words.append({"text": stripped, "confidence": conf})

        value, conf = _extract_numeric(words)

        # EasyOCR fallback: if Tesseract confidence is low, try EasyOCR
        if conf < CONFIDENCE_THRESHOLD and easyocr_available:
            try:
                # Save preprocessed image for EasyOCR
                import tempfile, os
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    processed.save(tmp.name)
                    tmp_path = tmp.name

                easy_result = scan_with_easyocr(tmp_path)
                easy_words = easy_result.get("words", [])

                if easy_words:
                    easy_value, easy_conf = _extract_numeric(easy_words)
                    # Use EasyOCR result if it's better
                    if easy_conf > conf:
                        value = easy_value
                        conf = easy_conf
                        words = easy_words
            except Exception:
                pass  # fallback failed, keep Tesseract result
            finally:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

        low_conf = conf < CONFIDENCE_THRESHOLD and value is not None

        if low_conf:
            flag = True

        fields[field_name] = {
            "value":      value,
            "confidence": conf,
            "raw_words":  [w["text"] for w in words[:5]],
            "low_conf":   low_conf,
        }

    return {
        "source_path": str(Path(file_path)),
        "fields":      fields,
        "flagged":     flag,
        "overall_confidence": round(
            sum(f["confidence"] for f in fields.values()) / max(len(fields), 1), 3
        ),
    }


# ── DB persistence ────────────────────────────────────────────────────────────

def persist_ocr_result(
    frame_path: str,
    fields: dict,
    session_id: int | None = None,
    upload_id: int | None  = None,
) -> int:
    """Save OCR result to ocr_results table. Returns row ID."""
    f = fields.get("fields", {})
    conn = get_connection()
    cur  = conn.execute(
        """INSERT INTO ocr_results
           (session_id, upload_id, frame_path,
            balance_value, bet_value, win_value,
            raw_text, confidence_avg,
            confidence_bal, confidence_bet, confidence_win, flagged)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            session_id,
            upload_id,
            frame_path,
            f.get("balance", {}).get("value"),
            f.get("bet",     {}).get("value"),
            f.get("win",     {}).get("value"),
            str(fields.get("fields", {})),
            fields.get("overall_confidence", 0),
            f.get("balance", {}).get("confidence", 0),
            f.get("bet",     {}).get("confidence", 0),
            f.get("win",     {}).get("confidence", 0),
            int(fields.get("flagged", False)),
        )
    )
    result_id = cur.lastrowid
    conn.commit()
    conn.close()
    return result_id
