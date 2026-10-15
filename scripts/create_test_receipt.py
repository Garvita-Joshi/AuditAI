"""Create a clean synthetic receipt for OCR integration testing."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "sample_receipt_ocr.png"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)


def font(size: int, bold: bool = False):
    filename = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    candidates = [
        Path("C:/Windows/Fonts") / filename,
        Path("C:/Users/aishi/anaconda3/Lib/site-packages/matplotlib/mpl-data/fonts/ttf") / filename,
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


image = Image.new("RGB", (1200, 1600), "white")
draw = ImageDraw.Draw(image)
dark = "#161616"
muted = "#575757"
orange = "#e9774f"

draw.rectangle((0, 0, 1200, 18), fill=orange)
draw.text((90, 70), "METRO BITES CAFE", font=font(48, True), fill=dark)
draw.text((92, 135), "Corporate Expense Receipt", font=font(25), fill=muted)
draw.line((90, 205, 1110, 205), fill="#222222", width=3)

details = [
    ("Invoice number", "TEST-2026-0042"),
    ("Date", "2026-09-29"),
    ("Vendor", "Metro Bites Cafe"),
    ("Employee", "Aishi Sharma"),
    ("Category", "Client Entertainment"),
]
y = 250
for label, value in details:
    draw.text((95, y), label.upper(), font=font(22, True), fill=muted)
    draw.text((475, y), value, font=font(27), fill=dark)
    y += 58

draw.line((90, 560, 1110, 560), fill="#222222", width=3)
draw.text((95, 605), "DESCRIPTION", font=font(22, True), fill=muted)
draw.text((760, 605), "AMOUNT", font=font(22, True), fill=muted)
draw.line((90, 650, 1110, 650), fill="#bdbdbd", width=2)

items = [("Client dinner", "₹1,250.00"), ("GST 18%", "₹225.00")]
y = 700
for label, value in items:
    draw.text((95, y), label, font=font(30), fill=dark)
    draw.text((790, y), value, font=font(30), fill=dark)
    y += 65

draw.line((90, 850, 1110, 850), fill="#222222", width=3)
draw.text((95, 900), "TOTAL", font=font(34, True), fill=dark)
draw.text((760, 895), "₹1,475.00", font=font(40, True), fill=orange)

draw.rounded_rectangle((90, 1010, 1110, 1140), radius=18, outline="#bbbbbb", width=3)
draw.text((125, 1040), "Payment method", font=font(22, True), fill=muted)
draw.text((500, 1035), "Corporate card", font=font(30), fill=dark)

draw.text((90, 1240), "Thank you for your business.", font=font(28), fill=dark)
draw.text((90, 1300), "This synthetic receipt is for AuditAI OCR testing.", font=font(22), fill=muted)
draw.text((90, 1450), "TEST DOCUMENT · NOT A REAL PURCHASE", font=font(21, True), fill=orange)

image.save(OUTPUT, format="PNG", optimize=True)
print(OUTPUT)
