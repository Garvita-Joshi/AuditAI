#!/usr/bin/env python3
"""
AuditAI — Tested Reference OCR Extraction & Validation Runner.
Based directly on user's tested reference script:
- Automatic Mac Homebrew / Linux / Windows Tesseract path detection
- Cropping of target region of interest (ROI)
- High-contrast PIL ImageEnhance.Contrast(4) enhancement
- Tesseract with --psm 6 (uniform text block)
- OCR noise character cleaning
- Error-tolerant regex for calls, milestone times, and receipt totals
- Call journey sequence validation
"""
import os
import sys
import re
from pathlib import Path
from PIL import Image, ImageEnhance
import pytesseract

# Auto-detect Tesseract executable
for candidate in [
    "/opt/homebrew/bin/tesseract",
    "/usr/local/bin/tesseract",
    "tesseract",
    "C:/Program Files/Tesseract-OCR/tesseract.exe",
]:
    if candidate and (os.path.exists(candidate) or candidate == "tesseract"):
        pytesseract.pytesseract.tesseract_cmd = candidate
        break

print(f"Using Tesseract: {pytesseract.pytesseract.tesseract_cmd}")

# Select target image
target_image = "image.png"
if len(sys.argv) > 1:
    target_image = sys.argv[1]
elif not os.path.exists("image.png"):
    if os.path.exists("data/sample_receipt_ocr.png"):
        target_image = "data/sample_receipt_ocr.png"
    elif os.path.exists("data/receipts/receipt_CLM-01660.png"):
        target_image = "data/receipts/receipt_CLM-01660.png"

print(f"Loading image: {target_image}")
if not os.path.exists(target_image):
    print(f"Error: Target image '{target_image}' not found.")
    sys.exit(1)

img = Image.open(target_image)
print(f"Image Size: {img.size}")

# ==========================
# CROP REGION (OPTIONAL / IF SPECIFIED)
# ==========================
# If full image is provided without specific crop, use full width
if target_image == "image.png" and img.width >= 400 and img.height >= 400:
    left = 200
    top = 50
    right = img.width
    bottom = min(400, img.height)
    cropped = img.crop((left, top, right, bottom))
else:
    cropped = img.copy()

# ==========================
# IMAGE PREPROCESSING (TESTED METHOD)
# ==========================
# Convert to grayscale and apply 4x contrast enhancement
cropped = cropped.convert("L")
cropped = ImageEnhance.Contrast(cropped).enhance(4)

debug_crop_path = "debug_crop.png"
cropped.save(debug_crop_path)
print(f"Saved preprocessed crop to {debug_crop_path}")

# ==========================
# OCR WITH PSM 6
# ==========================
text = pytesseract.image_to_string(cropped, config="--psm 6")

print("\n===== OCR RAW TEXT =====\n")
print(text.strip())

# ==========================
# CLEAN OCR TEXT (NOISE REDUCTION)
# ==========================
clean_text = text.lower()
for ch in [" ", "@", "©", ">", "\n", "\t", '"', "'", "`", "~", "*", "_"]:
    clean_text = clean_text.replace(ch, "")

print("\n===== CLEANED OCR =====\n")
print(clean_text)

# ==========================
# DETECT CALLS (ERROR-TOLERANT)
# ==========================
calls = re.findall(r"c[a4o0@][l1i\|]{2}|cal[l1i\|]|ca[l1i\|]l|call", clean_text)

# ==========================
# DETECT TIMES & DURATIONS
# ==========================
times = []
time_pattern = re.compile(r"([0-9oO]+d)?([0-9oO]+)[hHn]([0-9oO]+)[mM]")
raw_times = time_pattern.findall(clean_text)

for days, hours, mins in raw_times:
    days_str = days.replace("o", "0").replace("O", "0") if days else ""
    hours_str = hours.replace("o", "0").replace("O", "0")
    mins_str = mins.replace("o", "0").replace("O", "0")

    t = f"{days_str[:-1]}d {hours_str}h {mins_str}m" if days_str else f"{hours_str}h {mins_str}m"
    times.append(t)

# Remove duplicates while preserving order
times = list(dict.fromkeys(times))

print("\n===== DETECTED CALLS & TIMINGS =====")
print(f"CALL COUNT: {len(calls)}")
print(f"TIMES: {times}")

# ==========================
# DETECT FINANCIAL TOTALS (IF RECEIPT)
# ==========================
amount_pattern = re.compile(
    r"(?:grand\s*total|total\s*(?:amount|due|payable)?|amount\s*(?:due|payable)?|net\s*(?:amount|total)|balance\s*due)"
    r"\s*[:=\-]?\s*(?:[₹$€£]|inr|rs\.?|usd)?\s*([0-9oOIl][0-9oOIl,\.]*)",
    re.IGNORECASE,
)
match_amount = amount_pattern.search(text)
if match_amount:
    raw_amt = (
        match_amount.group(1)
        .replace("o", "0")
        .replace("O", "0")
        .replace("I", "1")
        .replace("l", "1")
        .replace("|", "1")
        .replace(",", "")
    )
    print(f"\nDETECTED RECEIPT TOTAL: {raw_amt}")

# ==========================
# BUILD JOURNEY (IF CALL TIMELINE)
# ==========================
if times:
    print("\n===== JOURNEY =====\n")
    for i, t in enumerate(times):
        print(f"CALL ({t})")
        if i < len(times) - 1:
            print(f"↓ after {times[i + 1]}")

print("\n✓ OCR Extraction Complete.")
