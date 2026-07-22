"""
Generate synthetic test frames for OCR benchmarking.
Creates PIL images with known text at known positions (simulating slot UI).
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import random

OUT = Path(__file__).parent
OUT.mkdir(exist_ok=True)

def _text_size(draw, text, font):
    """Get bounding box of text."""
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]

def make_test_frame(
    balance="$1,234.56",
    bet="$2.00",
    win="$15.00",
    bonus="$0.00",
    jackpot="$0.00",
    filename="test_frame_1.png",
):
    """Create a 1280x720 slot-like frame with text at expected positions."""
    img = Image.new("RGB", (1280, 720), color=(10, 10, 30))
    draw = ImageDraw.Draw(img)

    try:
        font_large = ImageFont.truetype("arial.ttf", 36)
        font_small = ImageFont.truetype("arial.ttf", 28)
    except Exception:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Balance — top left (matches Generic Slot profile: balance_region [10,10,200,50])
    draw.text((10, 10), f"BALANCE: {balance}", fill=(255, 220, 50), font=font_large)
    # Bet — middle left (matches profile: bet_region [10,60,150,30])
    draw.text((10, 60), f"BET: {bet}", fill=(200, 200, 200), font=font_large)
    # Win — middle left lower (matches profile: win_region [10,100,200,50])
    draw.text((10, 100), f"WIN: {win}", fill=(0, 255, 100), font=font_large)
    # Bonus — bottom left area
    draw.text((10, 140), f"BONUS: {bonus}", fill=(255, 150, 0), font=font_large)
    # Jackpot — top right
    draw.text((900, 10), f"JACKPOT: {jackpot}", fill=(255, 215, 0), font=font_large)

    img.save(OUT / filename)
    return str(OUT / filename)

if __name__ == "__main__":
    make_test_frame(filename="frame_balanced.png")
    make_test_frame(balance="$500.00", bet="$1.00", win="$0.00", filename="frame_losing.png")
    make_test_frame(balance="$2,500.00", bet="$5.00", win="$50.00", bonus="$12.00", filename="frame_bonus.png")
    make_test_frame(jackpot="$10,000.00", filename="frame_jackpot.png")
    print(f"Generated fixtures in {OUT}")