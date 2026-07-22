"""
engines/frame_annotator.py
--------------------------
Annotate video frames with ROI boxes and OCR text overlay for debug export.
"""

from __future__ import annotations
import io
import zipfile
from pathlib import Path
from typing import Optional

import cv2
import numpy as np


COLORS = {
    "balance": (0, 255, 0),
    "bet":     (255, 165, 0),
    "win":     (0, 191, 255),
    "default": (255, 255, 0),
}


def annotate_frame(
    frame_path: str,
    ocr_data: dict,
    output_path: str,
) -> bool:
    """
    Draw ROI boxes and OCR text on a frame. Returns True on success.

    ocr_data format:
    {
        "balance": {"value": 100.0, "confidence": 0.9, "bbox": [x1, y1, x2, y2]},
        "bet":     {"value": 10.0,  "confidence": 0.85, "bbox": [250, 100, 350, 200]},
    }
    """
    img = cv2.imread(frame_path)
    if img is None:
        return False

    for field_name, data in ocr_data.items():
        bbox = data.get("bbox")
        value = data.get("value")
        confidence = data.get("confidence", 0.0)

        if bbox and len(bbox) == 4:
            x1, y1, x2, y2 = [int(v) for v in bbox]
            color = COLORS.get(field_name, COLORS["default"])

            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)

            label = f"{field_name}: ${value:.2f} ({confidence:.0%})" if value is not None else field_name
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(img, (x1, y1 - th - 8), (x1 + tw + 4, y1), color, -1)

            cv2.putText(img, label, (x1 + 2, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

    cv2.imwrite(output_path, img)
    return True


def create_annotated_zip(
    frames_data: list[dict],
    output_zip_path: Optional[str] = None,
) -> bytes | str:
    """
    Create a ZIP archive of annotated frames.

    frames_data: [{"frame_path": "...", "ocr_data": {...}}, ...]
    Returns bytes if output_zip_path is None, else writes to path and returns path.
    """
    buf = io.BytesIO() if output_zip_path is None else None

    with zipfile.ZipFile(buf or output_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, frame_info in enumerate(frames_data):
            frame_path = frame_info["frame_path"]
            ocr_data = frame_info.get("ocr_data", {})

            img = cv2.imread(frame_path)
            if img is None:
                continue

            for field_name, data in ocr_data.items():
                bbox = data.get("bbox")
                value = data.get("value")
                confidence = data.get("confidence", 0.0)

                if bbox and len(bbox) == 4:
                    x1, y1, x2, y2 = [int(v) for v in bbox]
                    color = COLORS.get(field_name, COLORS["default"])
                    cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
                    label = f"{field_name}: ${value:.2f} ({confidence:.0%})" if value is not None else field_name
                    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                    cv2.rectangle(img, (x1, y1 - th - 8), (x1 + tw + 4, y1), color, -1)
                    cv2.putText(img, label, (x1 + 2, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

            _, encoded = cv2.imencode(".jpg", img)
            arcname = f"frame_{i:04d}_annotated.jpg"
            zf.writestr(arcname, encoded.tobytes())

    if buf is not None:
        return buf.getvalue()
    return output_zip_path
