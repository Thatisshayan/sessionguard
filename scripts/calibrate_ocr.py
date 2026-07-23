"""
scripts/calibrate_ocr.py
-------------------------
Run this script with a screenshot of your game to find
the exact pixel coordinates for balance, bet, and win regions.

Usage:
  python scripts/calibrate_ocr.py "C:\path\to\screenshot.png"

It will print the detected regions and save a calibrated profile.
"""
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def calibrate(image_path: str):
    from engines.ocr_engine import scan_image

    print(f"\n=== OCR CALIBRATION ===")
    print(f"Scanning: {image_path}\n")

    result = scan_image(image_path)
    words  = result.get("words", [])

    if not words:
        print("No text detected. Check the image path.")
        return

    print(f"Detected {len(words)} text regions:\n")
    print(f"{'Text':<20} {'Confidence':>10}  {'X':>5} {'Y':>5} {'W':>5} {'H':>5}  ROI")
    print("-" * 80)

    # Filter to likely numeric values (balance/bet/win are numbers)
    numeric = []
    for w in words:
        txt = w["text"].strip()
        # Keep if it looks like a number or currency
        clean = txt.replace("$","").replace(",","").replace(".","").replace("-","")
        if clean.isdigit() and len(clean) >= 1:
            numeric.append(w)
            marker = " <-- NUMERIC"
        else:
            marker = ""
        conf = w["confidence"]
        roi  = f"[{w['left']}, {w['top']}, {w['width']}, {w['height']}]"
        print(f"{txt:<20} {conf:>10.1f}  {w['left']:>5} {w['top']:>5} {w['width']:>5} {w['height']:>5}  {roi}{marker}")

    print(f"\n=== NUMERIC VALUES FOUND ===")
    if not numeric:
        print("No numeric values detected — try a screenshot while numbers are visible on screen.")
        return

    for w in numeric:
        print(f"  '{w['text']}' at x={w['left']}, y={w['top']}, w={w['width']}, h={w['height']}  (conf: {w['confidence']:.0f}%)")

    print(f"\n=== INSTRUCTIONS ===")
    print("1. Look at the list above")
    print("2. Find the rows matching your BALANCE, BET, and WIN values")
    print("3. Note their ROI coordinates [x, y, width, height]")
    print("4. Tell the AI those coordinates — I'll save them to your profile")
    print("\nTip: Add padding around the number (e.g. add 20px to width/height)")
    print("     to make sure the full value is captured during live play.\n")

    # Save raw scan for reference
    out = ROOT / "storage" / "ocr_calibration_scan.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"words": words, "numeric": numeric}, indent=2))
    print(f"Full scan saved to: {out}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/calibrate_ocr.py <path_to_screenshot>")
        print("Example: python scripts/calibrate_ocr.py C:\\Screenshots\\game.png")
        sys.exit(1)
    calibrate(sys.argv[1])
