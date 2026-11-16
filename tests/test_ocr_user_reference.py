"""
Tests based directly on user's tested reference snippet for robust OCR extraction:
- High contrast PIL ImageEnhance.Contrast(img).enhance(4)
- Tesseract with --psm 6
- Noise cleaning
- Error-tolerant regex for calls, times, and receipt totals
- Journey sequence validation
"""
import os
import re
import pytest
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import pytesseract

from backend.app.config import TESSERACT_CMD
from backend.app.ocr.preprocess import enhance_contrast, crop_image, preprocess_image
from backend.app.ocr.engine import ocr_engine
from backend.app.ocr.extractor import (
    extract_fields,
    extract_call_journey_from_text,
    _extract_amount_regex,
    _clean_numeric_ocr,
)


@pytest.fixture(autouse=True)
def setup_tesseract():
    if os.path.exists("/opt/homebrew/bin/tesseract"):
        pytesseract.pytesseract.tesseract_cmd = "/opt/homebrew/bin/tesseract"
    elif os.path.exists(TESSERACT_CMD):
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD


def test_user_reference_call_journey_logic():
    """Verify the exact regex, noise cleaning, and journey logic from user's script."""
    # Simulated noisy OCR text containing calls and timestamps with OCR character substitutions
    raw_ocr = """
    @ > CALL (0h 0m)
    © ↓ after 1d 0h 0m
    CaLL (1d Oh Om)
    ↓ after 2d 0h 0m
    c4ll (2d oh om)
    """

    res = extract_call_journey_from_text(raw_ocr)
    assert res["call_count"] == 3
    assert res["times"] == ["0h 0m", "1d 0h 0m", "2d 0h 0m"]
    assert len(res["journey"]) == 3
    assert res["journey"][0]["next_step_after"] == "1d 0h 0m"
    assert res["journey"][1]["next_step_after"] == "2d 0h 0m"


def test_user_reference_image_contrast_and_crop(tmp_path):
    """Test PIL contrast enhancement and cropping as specified in user reference."""
    # Create synthetic test card image with text
    img = Image.new("RGB", (600, 300), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((220, 80), "CALL 0h 0m", fill="black")
    draw.text((220, 140), "CALL 1d 0h 0m", fill="black")
    draw.text((220, 200), "CALL 2d 0h 0m", fill="black")

    img_path = str(tmp_path / "journey_screenshot.png")
    img.save(img_path)

    # Apply crop as in user reference
    left, top, right, bottom = 200, 50, img.width, 250
    cropped = img.crop((left, top, right, bottom))
    cropped = cropped.convert("L")
    enhanced = ImageEnhance.Contrast(cropped).enhance(4)

    # Run Tesseract with --psm 6
    text = pytesseract.image_to_string(enhanced, config="--psm 6")
    journey = extract_call_journey_from_text(text)

    assert journey["call_count"] >= 3
    assert "0h 0m" in journey["times"]
    assert "1d 0h 0m" in journey["times"]


def test_error_tolerant_amount_parsing():
    """Test that amount extraction handles OCR substitutions (o/O -> 0, l/I -> 1)."""
    assert _clean_numeric_ocr("1,250.00") == 1250.0
    assert _clean_numeric_ocr("l,475.oo") == 1475.0  # lowercase L and O
    assert _clean_numeric_ocr("$0247.14") == 247.14
    assert _clean_numeric_ocr("1O247.14") == 10247.14  # capital O
    assert _clean_numeric_ocr("70834") == 70834.0


def test_receipt_ocr_accuracy_on_real_samples():
    """Verify high accuracy on repository sample receipts using enhanced Tesseract engine."""
    sample_path = "data/sample_receipt_ocr.png"
    if os.path.exists(sample_path):
        preprocessed = preprocess_image(sample_path, contrast_factor=3.5)
        text, conf, method = ocr_engine.extract_text(preprocessed)
        fields = extract_fields(text, use_llm_fallback=False)

        assert method == "tesseract"
        assert fields["amount"] == 1475.0
        assert "METRO BITES" in (fields["vendor"] or "").upper()
        assert fields["date"] == "2026-09-29"


def test_clm_receipt_ocr_extracts_clean_vendor_and_date():
    """Verify Makemytrip receipt extracts clean vendor, date, and tax ID."""
    receipt_path = "data/receipts/receipt_CLM-01660.png"
    if os.path.exists(receipt_path):
        preprocessed = preprocess_image(receipt_path, contrast_factor=4.0)
        text, conf, method = ocr_engine.extract_text(preprocessed)
        fields = extract_fields(text, use_llm_fallback=False)

        assert method == "tesseract"
        assert "MAKEMYTRIP" in (fields["vendor"] or "").upper()
        assert fields["date"] == "2026-11-21"
        assert fields["amount"] is not None
