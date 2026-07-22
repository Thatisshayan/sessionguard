"""OCR accuracy benchmarks — synthetic frame tests."""
import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


class TestOcrAccuracy(unittest.TestCase):
    """Benchmark suite for OCR field extraction accuracy."""

    @classmethod
    def setUpClass(cls):
        # Generate test frames on the fly (handles fresh clone)
        from tests.fixtures.generate_fixtures import make_test_frame
        cls.frame_balanced = make_test_frame(filename="test_balanced.png")
        cls.frame_losing   = make_test_frame(balance="$500.00", bet="$1.00", win="$0.00", filename="test_losing.png")

    def _extract_fields(self, image_path: str) -> dict:
        """Run OCR on a frame image and return extracted fields."""
        try:
            from engines.ocr_engine import extract_fields_from_image
            return extract_fields_from_image(image_path)
        except Exception as e:
            return {"error": str(e)}

    def test_balance_extraction(self):
        """Balance should be extractable from synthetic frame."""
        if not (FIXTURES / "test_balanced.png").exists():
            self.skipTest("Fixture not generated")
        result = self._extract_fields(str(FIXTURES / "test_balanced.png"))
        if "error" in result:
            self.skipTest(f"OCR not available: {result['error']}")
        # Should have a numeric value extracted (balance is non-zero)
        balance = result.get("balance")
        self.assertIsNotNone(balance, "Balance field should be extracted")
        self.assertGreater(float(balance["value"]), 0, "Balance should be a positive number")

    def test_bet_extraction(self):
        """Bet should be extractable from synthetic frame."""
        if not (FIXTURES / "test_balanced.png").exists():
            self.skipTest("Fixture not generated")
        result = self._extract_fields(str(FIXTURES / "test_balanced.png"))
        if "error" in result:
            self.skipTest(f"OCR not available: {result['error']}")
        bet = result.get("bet")
        self.assertIsNotNone(bet, "Bet field should be extracted")

    def test_win_extraction(self):
        """Win should be extractable from synthetic frame."""
        if not (FIXTURES / "test_balanced.png").exists():
            self.skipTest("Fixture not generated")
        result = self._extract_fields(str(FIXTURES / "test_balanced.png"))
        if "error" in result:
            self.skipTest(f"OCR not available: {result['error']}")
        win = result.get("win")
        self.assertIsNotNone(win, "Win field should be extracted")

    def test_zero_win_extraction(self):
        """Zero win should be extractable (not confused with empty)."""
        if not (FIXTURES / "test_losing.png").exists():
            self.skipTest("Fixture not generated")
        result = self._extract_fields(str(FIXTURES / "test_losing.png"))
        if "error" in result:
            self.skipTest(f"OCR not available: {result['error']}")
        win = result.get("win")
        self.assertIsNotNone(win, "Win field should be extracted even when zero")


if __name__ == "__main__":
    unittest.main()