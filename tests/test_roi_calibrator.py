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


def test_label_for_region_uses_above_label_when_left_is_empty(monkeypatch, tmp_path):
    """The label lookup also scans *above* the region when the left crop is
    OCR-empty. Covers the second OCR-scan branch."""
    image_path = tmp_path / "screen.png"
    Image.new("RGB", (240, 200), "white").save(image_path)
    calls = {"n": 0}
    def _fake_ocr(_crop):
        calls["n"] += 1
        return "" if calls["n"] == 1 else "Wager"
    monkeypatch.setattr(roi_calibrator, "_ocr_label_image", _fake_ocr)

    # x=120 leaves a wide-enough left strip (margin=80) so the left branch
    # fires first; it returns "" forcing the above branch, which returns "Wager".
    region = {"x": 120, "y": 120, "w": 40, "h": 20}
    result = roi_calibrator._label_for_region(str(image_path), region, margin=80)
    assert result == "bet"
    assert calls["n"] == 2


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


def test_region_has_numeric_returns_false_on_non_numeric(monkeypatch, tmp_path):
    image_path = tmp_path / "screen.png"
    Image.new("RGB", (100, 100), "white").save(image_path)

    class FakeTesseract:
        @staticmethod
        def image_to_string(_image, config):
            return "labels only no digits here"

    monkeypatch.setitem(__import__("sys").modules, "pytesseract", FakeTesseract)
    assert roi_calibrator._region_has_numeric(
        str(image_path), {"x": 10, "y": 10, "w": 60, "h": 20}
    ) is False


class TestAutoCalibrateRoi:
    def test_returns_failure_for_missing_file(self, tmp_path):
        result = roi_calibrator.auto_calibrate_roi(str(tmp_path / "nope.png"))
        assert result["success"] is False
        assert "File not found" in result["error"]
        assert result["roi_config"] == {}

    def test_returns_failure_when_no_text_regions_detected(self, monkeypatch, tmp_path):
        image_path = tmp_path / "blank.png"
        Image.new("RGB", (200, 200), "white").save(image_path)
        # Force contour detection to return nothing for this image.
        monkeypatch.setattr(roi_calibrator, "_find_text_regions", lambda _p: [])
        result = roi_calibrator.auto_calibrate_roi(str(image_path))
        assert result["success"] is False
        assert "No text regions" in result["error"]
        assert result["detected_regions"] == []

    def test_labels_known_regions_and_builds_config(self, monkeypatch, tmp_path):
        image_path = tmp_path / "screen.png"
        Image.new("RGB", (300, 300), "white").save(image_path)
        regions = [
            {"x": 10, "y": 30, "w": 80, "h": 20, "area": 1600, "aspect_ratio": 4.0,
             "cx": 50, "cy": 40},
            {"x": 10, "y": 70, "w": 80, "h": 20, "area": 1600, "aspect_ratio": 4.0,
             "cx": 50, "cy": 80},
            {"x": 10, "y": 110, "w": 80, "h": 20, "area": 1600, "aspect_ratio": 4.0,
             "cx": 50, "cy": 120},
        ]
        monkeypatch.setattr(roi_calibrator, "_find_text_regions", lambda _p: regions)

        # Round-robin the labels across the three regions.
        labels = iter(["balance", "bet", "win"])
        monkeypatch.setattr(roi_calibrator, "_label_for_region",
                            lambda _p, _r, _m=80: next(labels))
        # And confirm each region has numeric data so it's accepted.
        monkeypatch.setattr(roi_calibrator, "_region_has_numeric", lambda *_a, **_k: True)

        result = roi_calibrator.auto_calibrate_roi(str(image_path))
        assert result["success"] is True
        assert result["confidence"] == 1.0
        assert set(result["roi_config"]) == {"balance_region", "bet_region", "win_region"}
        assert result["labels_found"] == {"balance": True, "bet": True, "win": True}
        assert result["detected_regions"] == regions

    def test_falls_back_to_positional_guess_when_no_labels(self, monkeypatch, tmp_path):
        image_path = tmp_path / "screen.png"
        Image.new("RGB", (300, 300), "white").save(image_path)
        regions = [
            {"x": 10, "y": 30, "w": 80, "h": 20, "area": 1600, "aspect_ratio": 4.0,
             "cx": 50, "cy": 40},
            {"x": 10, "y": 70, "w": 80, "h": 20, "area": 1600, "aspect_ratio": 4.0,
             "cx": 50, "cy": 80},
            {"x": 10, "y": 110, "w": 80, "h": 20, "area": 1600, "aspect_ratio": 4.0,
             "cx": 50, "cy": 120},
            {"x": 200, "y": 200, "w": 10, "h": 10, "area": 100, "aspect_ratio": 1.0,
             "cx": 205, "cy": 205},
        ]
        monkeypatch.setattr(roi_calibrator, "_find_text_regions", lambda _p: regions)
        monkeypatch.setattr(roi_calibrator, "_label_for_region", lambda *_a, **_k: None)
        # First three regions are numeric; the fourth is noise — exercises the
        # value_regions filter (>= 3 numeric kept).
        numeric_map = {id(r): (i < 3) for i, r in enumerate(regions)}
        monkeypatch.setattr(
            roi_calibrator, "_region_has_numeric",
            lambda _p, r: numeric_map.get(id(r), False)
        )
        result = roi_calibrator.auto_calibrate_roi(str(image_path))
        assert result["success"] is True
        assert result["confidence"] == 0.5  # lowered confidence for positional guess
        assert result["labels_found"] == {"balance": True, "bet": True, "win": True}


class TestBuildMessage:
    def test_high_confidence_message(self):
        msg = roi_calibrator._build_message(
            {"balance": True, "bet": True, "win": True}, 1.0, 5)
        assert "high confidence" in msg
        assert "Identified: balance, bet, win" in msg

    def test_medium_confidence_message_lists_missing(self):
        msg = roi_calibrator._build_message(
            {"balance": True, "bet": False, "win": False}, 0.5, 3)
        assert "verify regions manually" in msg
        assert "Missing: bet, win" in msg

    def test_low_confidence_message_recommends_manual(self):
        msg = roi_calibrator._build_message(
            {"balance": False, "bet": False, "win": False}, 0.0, 9)
        assert "manual calibration recommended" in msg
        assert "Missing: balance, bet, win" in msg
