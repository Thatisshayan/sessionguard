import pytest
import tempfile
import zipfile
from pathlib import Path
from engines.frame_annotator import annotate_frame, create_annotated_zip


def _create_test_frame(tmp_path: Path) -> str:
    import cv2
    import numpy as np
    frame_path = str(tmp_path / "frame_001.jpg")
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    img[100:200, 100:300] = [255, 255, 255]
    cv2.imwrite(frame_path, img)
    return frame_path


class TestAnnotateFrame:
    def test_creates_annotated_image(self, tmp_path):
        frame_path = _create_test_frame(tmp_path)
        ocr_data = {
            "balance": {"value": 100.0, "confidence": 0.9, "bbox": [100, 100, 200, 200]},
            "bet": {"value": 10.0, "confidence": 0.85, "bbox": [250, 100, 350, 200]},
        }
        output_path = str(tmp_path / "annotated_001.jpg")
        result = annotate_frame(frame_path, ocr_data, output_path)
        assert result is True
        assert Path(output_path).exists()

    def test_returns_false_on_missing_frame(self, tmp_path):
        result = annotate_frame("/nonexistent/frame.jpg", {}, str(tmp_path / "out.jpg"))
        assert result is False


class TestCreateAnnotatedZip:
    def test_creates_valid_zip(self, tmp_path):
        frame_path = _create_test_frame(tmp_path)
        frames_data = [
            {"frame_path": frame_path, "ocr_data": {"balance": {"value": 100, "confidence": 0.9, "bbox": [100, 100, 200, 200]}}},
        ]
        zip_path = str(tmp_path / "annotated.zip")
        result = create_annotated_zip(frames_data, output_zip_path=zip_path)
        assert result == zip_path
        assert Path(zip_path).exists()
        with zipfile.ZipFile(zip_path) as zf:
            assert len(zf.namelist()) == 1
            assert zf.namelist()[0].endswith(".jpg")

    def test_returns_bytes_when_no_path(self, tmp_path):
        frame_path = _create_test_frame(tmp_path)
        frames_data = [
            {"frame_path": frame_path, "ocr_data": {}},
        ]
        result = create_annotated_zip(frames_data)
        assert isinstance(result, bytes)
        assert len(result) > 0
