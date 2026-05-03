"""
backend/routes/ocr_calibrate.py
---------------------------------
OCR calibration helper.
Upload a screenshot → get detected regions highlighted → adjust ROI.
POST /ocr-calibrate/scan   -- scan image, return all detected text with positions
POST /ocr-calibrate/test   -- test specific ROI coordinates on an image
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from pathlib import Path
import tempfile, json, shutil

router = APIRouter(tags=["ocr-calibrate"])


@router.post("/ocr-calibrate/scan")
async def scan_full(file: UploadFile = File(...)):
    """
    Scan a full screenshot and return ALL detected text with pixel positions.
    Use this to find the correct ROI coordinates for balance/bet/win fields.
    """
    suffix = Path(file.filename or 'img.png').suffix or '.png'
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        from engines.ocr_engine import scan_image
        result = scan_image(tmp_path)

        # Group nearby words into lines for easier reading
        words = result.get('words', [])
        lines = []
        if words:
            words_sorted = sorted(words, key=lambda w: (w['top'] // 20, w['left']))
            current_line = [words_sorted[0]]
            for word in words_sorted[1:]:
                if abs(word['top'] - current_line[-1]['top']) < 20:
                    current_line.append(word)
                else:
                    lines.append(current_line)
                    current_line = [word]
            lines.append(current_line)

        line_results = []
        for line in lines:
            text  = ' '.join(w['text'] for w in line)
            x     = min(w['left'] for w in line)
            y     = min(w['top']  for w in line)
            w_end = max(w['left'] + w['width'] for w in line)
            h_end = max(w['top']  + w['height']for w in line)
            conf  = round(sum(w['confidence'] for w in line) / len(line), 1)
            line_results.append({
                'text':       text,
                'x':          x,
                'y':          y,
                'width':      w_end - x,
                'height':     h_end - y,
                'confidence': conf,
                'roi':        [x, y, w_end - x, h_end - y],
            })

        return {
            'success':      True,
            'word_count':   len(words),
            'lines':        line_results,
            'tip':          'Find your balance/bet/win values in the list. Use the x/y/width/height as your ROI coordinates.',
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@router.post("/ocr-calibrate/test-roi")
async def test_roi(
    file:    UploadFile = File(...),
    x:       int  = Form(0),
    y:       int  = Form(0),
    w:       int  = Form(200),
    h:       int  = Form(60),
    scale:   float = Form(2.0),
):
    """
    Crop to exact ROI and OCR just that region.
    Use to verify your ROI coordinates hit the right number.
    """
    suffix = Path(file.filename or 'img.png').suffix or '.png'
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        from PIL import Image
        import pytesseract

        img = Image.open(tmp_path)
        iw, ih = img.size

        # Clamp ROI to image bounds
        x1 = max(0, x);      y1 = max(0, y)
        x2 = min(iw, x + w); y2 = min(ih, y + h)

        if x2 <= x1 or y2 <= y1:
            raise HTTPException(status_code=400, detail="ROI is outside image bounds.")

        cropped = img.crop((x1, y1, x2, y2))
        if scale != 1.0:
            new_w = int(cropped.width  * scale)
            new_h = int(cropped.height * scale)
            cropped = cropped.resize((new_w, new_h), Image.LANCZOS)

        # Convert to grayscale + threshold for better OCR
        gray = cropped.convert('L')
        text = pytesseract.image_to_string(
            gray,
            config='--psm 8 --oem 3 -c tessedit_char_whitelist=0123456789.$,.'
        ).strip()

        data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
        confs = [float(c) for c in data['conf'] if float(c) >= 0]
        avg_conf = round(sum(confs)/len(confs), 1) if confs else 0

        return {
            'success':      True,
            'detected':     text,
            'confidence':   avg_conf,
            'roi_used':     [x1, y1, x2-x1, y2-y1],
            'image_size':   [iw, ih],
            'tip':          'If confidence < 80, try adjusting x/y/w/h or increasing scale.',
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        Path(tmp_path).unlink(missing_ok=True)
