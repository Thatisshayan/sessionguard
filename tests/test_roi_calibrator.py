"""First regression coverage for screenshot ROI calibration helpers."""

from PIL import Image

import engines.roi_calibrator as roi_calibrator


def test_find_text_regions_returns_empty_for_missing_image(tmp_path):
    assert roi_calibrator._find_text_regions(str(tmp_path / "missing.png")) == []


def test_label_for_region_uses_left_hand_field_label(monkeypatch, tmp_path):
    image_path = tmp_path / "screen.png"
    Image.new("RGB", (240, 160), "white").save(image_path)
    monkeypatch.setattr(roi_calibrator, "_ocr_label_image", lambda _crop: "Balance")

    result = roi_calibrator._label_for_region(
        str(image_path), {"x": 120, "y": 60, "w": 40, "h": 20}
    )

    assert result == "balance"


def test_region_has_numeric_handles_ocr_result(monkeypatch, tmp_path):
    image_path = tmp_path / "screen.png"
    Image.new("RGB", (100, 100), "white").save(image_path)

    class FakeTesseract:
        @staticmethod
        def image_to_string(_image, config):
            assert "psm 7" in config
            return "Balance 1,234.50"

    monkeypatch.setitem(__import__("sys").modules, "pytesseract", FakeTesseract)

    assert roi_calibrator._region_has_numeric(
        str(image_path), {"x": 10, "y": 10, "w": 60, "h": 20}
    ) is True
