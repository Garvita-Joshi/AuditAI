"""
AuditAI — Structured field extraction from raw OCR text.

Two-strategy approach:
  1. Regex-based pattern matching (fast, deterministic)
  2. Gemini LLM fallback for incomplete extractions

Outputs a strict JSON-compatible dict with: vendor, amount, date, tax_id,
line_items, and an overall confidence score.
"""
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────
# Regex Patterns
# ──────────────────────────────────────────

# Amount patterns — look for "Total", "Amount", "Grand Total" followed by a number
_AMOUNT_PATTERNS = [
    re.compile(
        r"(?:grand\s*total|total\s*(?:amount|due|payable)?|amount\s*(?:due|payable)?|net\s*(?:amount|total)|balance\s*due)"
        r"\s*[:=\-]?\s*(?:[₹$€£]|inr|rs\.?|usd)?\s*([0-9oOIl|,\.]+)",
        re.IGNORECASE,
    ),
    # Matches "TOTAL $10247.14" or "TOTAL: 1,475.00" or "TOTAL 5000"
    re.compile(
        r"(?:^|\n)\s*(?:total|amount|net|due)\s*[:=\-]?\s*[$₹€£]?\s*([0-9oOIl][0-9oOIl,\.]*)",
        re.IGNORECASE,
    ),
    # Standalone currency amount on a line (fallback)
    re.compile(r"[₹$€£]\s*([0-9oOIl,]+\.[0-9oOIl]{2})\s*$", re.MULTILINE),
]

# Date patterns
_DATE_PATTERNS = [
    # YYYY-MM-DD or YYYY/MM/DD
    re.compile(r"\b(\d{4}[-/]\d{1,2}[-/]\d{1,2})\b"),
    # DD/MM/YYYY or DD-MM-YYYY
    re.compile(r"\b(\d{1,2}[-/]\d{1,2}[-/]\d{4})\b"),
    # Dt: 2026-11-21 or Date: 2026-11-21
    re.compile(r"(?:date|dt|dated)\s*[:=\-]?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})", re.IGNORECASE),
    # Mon DD, YYYY or DD Mon YYYY
    re.compile(
        r"\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*"
        r"[\s,]+\d{4})\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*"
        r"\s+\d{1,2}[\s,]+\d{4})\b",
        re.IGNORECASE,
    ),
]

# Tax ID patterns
_TAX_PATTERNS = [
    # Indian GST: 2-digit state code + 10-char PAN + entity code + Z + check digit
    re.compile(r"\b(\d{2}[A-Z]{5}\d{4}[A-Z]\d[Z][A-Z\d])\b"),
    # Common OCR tax label with spaces or minor misreads: TAXID 27 AABCUBGORIZ2
    re.compile(r"(?:tax\s*id|gstin?|tin)\s*[:=\-]?\s*([A-Z0-9\s\-]{8,22})", re.IGNORECASE),
    # US EIN
    re.compile(r"\b(\d{2}-\d{7})\b"),
]

# Line item: text followed by an amount
_LINE_ITEM_PATTERN = re.compile(
    r"^(.{3,40}?)\s+[$₹€£]?\s*([0-9oOIl,]+\.[0-9oOIl]{2})\s*$", re.MULTILINE
)


def _clean_numeric_ocr(raw_val: str) -> Optional[float]:
    """
    Error-tolerant digit parser that corrects common OCR character substitutions.
    'o'/'O' -> '0', 'I'/'l'/'|' -> '1', strips non-numeric noise while preserving decimals.
    """
    if not raw_val:
        return None
    cleaned = (
        raw_val.replace("o", "0")
        .replace("O", "0")
        .replace("I", "1")
        .replace("l", "1")
        .replace("|", "1")
        .replace(" ", "")
        .replace(",", "")
    )
    cleaned = re.sub(r"[^0-9.]", "", cleaned)
    # Handle multiple periods (keep only the last one)
    if cleaned.count(".") > 1:
        parts = cleaned.split(".")
        cleaned = "".join(parts[:-1]) + "." + parts[-1]
    try:
        val = float(cleaned)
        return val if val > 0 else None
    except ValueError:
        return None


def _extract_vendor_regex(text: str) -> Optional[str]:
    """Extract vendor name: checks explicit vendor label first, then first non-header line."""
    # Strategy 1: Explicit Vendor/Supplier label
    match = re.search(
        r"(?:^|\n)\s*(?:vendor|merchant|seller|supplier|store)\s*[:=\-]?\s*([A-Za-z0-9\s&'.-]{3,50}?)(?:\r?\n|$)",
        text,
        re.IGNORECASE,
    )
    if match:
        vendor = match.group(1).strip()
        if len(vendor) >= 3 and not re.match(r"^[\d\s\-/.,₹$]+$", vendor):
            return vendor

    # Strategy 2: First non-empty, non-header line
    header_blacklist = {
        "receipt", "invoice", "tax invoice", "bill", "cash receipt",
        "corporate expense receipt", "expense receipt", "official receipt",
        "retail invoice", "cash memo"
    }
    for line in text.split("\n"):
        cleaned = line.strip().strip("“\"'‘`*~_#>")
        if not cleaned:
            continue
        if cleaned.lower() in header_blacklist:
            continue
        # Skip lines that are purely numeric, dates, tax markers, or very short
        if re.match(r"^[\d\s\-/.,₹$]+$", cleaned):
            continue
        if re.search(r"^(?:date|dt|tax\s*id|invoice\s*number|tel|receipt\s*number)", cleaned, re.IGNORECASE):
            continue
        if len(cleaned) < 3:
            continue
        return cleaned
    return None


def _extract_amount_regex(text: str) -> Optional[float]:
    """Extract the total amount from receipt text with OCR error correction."""
    for pattern in _AMOUNT_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            # Check matches in reverse (grand totals typically appear at bottom)
            for m in reversed(matches):
                amt = _clean_numeric_ocr(m)
                if amt is not None:
                    return amt
    return None


def _extract_date_regex(text: str) -> Optional[str]:
    """Extract the first recognizable date from text."""
    for pattern in _DATE_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1).strip()
    return None


def _extract_tax_id_regex(text: str) -> Optional[str]:
    """Extract tax identification number (GST, EIN, VAT)."""
    for pattern in _TAX_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1).strip()
    return None


def _extract_line_items_regex(text: str) -> List[Dict[str, Any]]:
    """Extract line items (description + amount) from receipt text."""
    items = []
    for match in _LINE_ITEM_PATTERN.finditer(text):
        description = match.group(1).strip()
        try:
            amount = float(match.group(2).replace(",", ""))
            items.append({"description": description, "amount": amount})
        except ValueError:
            continue
    return items


def _calculate_extraction_confidence(fields: Dict[str, Any]) -> float:
    """
    Score extraction quality from 0.0 to 1.0 based on how many fields
    were successfully extracted.

    Weighting: vendor (0.25), amount (0.30), date (0.25), tax_id (0.10), line_items (0.10)
    """
    score = 0.0
    if fields.get("vendor"):
        score += 0.25
    if fields.get("amount") is not None:
        score += 0.30
    if fields.get("date"):
        score += 0.25
    if fields.get("tax_id"):
        score += 0.10
    if fields.get("line_items"):
        score += 0.10
    return round(score, 2)


def extract_fields(
    raw_text: str,
    use_llm_fallback: bool = True,
) -> Dict[str, Any]:
    """
    Extract structured fields from raw OCR text.

    Strategy:
      1. Regex-based extraction (fast, deterministic)
      2. If extraction is incomplete and use_llm_fallback=True, call Gemini API

    Args:
        raw_text: Raw text output from OCR engine.
        use_llm_fallback: Whether to attempt Gemini API for incomplete extractions.

    Returns:
        Dict with keys: vendor, amount, date, tax_id, line_items, confidence
    """
    if not raw_text or not raw_text.strip():
        return {
            "vendor": None,
            "amount": None,
            "date": None,
            "tax_id": None,
            "line_items": [],
            "confidence": 0.0,
        }

    # Strategy 1: Regex extraction
    fields = {
        "vendor": _extract_vendor_regex(raw_text),
        "amount": _extract_amount_regex(raw_text),
        "date": _extract_date_regex(raw_text),
        "tax_id": _extract_tax_id_regex(raw_text),
        "line_items": _extract_line_items_regex(raw_text),
    }

    confidence = _calculate_extraction_confidence(fields)
    fields["confidence"] = confidence

    # Strategy 2: Gemini LLM fallback for incomplete extractions
    filled_count = sum(
        1 for k in ["vendor", "amount", "date"]
        if fields.get(k) is not None
    )

    if use_llm_fallback and filled_count < 3:
        try:
            from backend.app.llm.gemini import extract_receipt_fields

            llm_fields = extract_receipt_fields(raw_text)
            if llm_fields:
                # Merge: LLM fills gaps, regex results take priority
                if not fields["vendor"] and llm_fields.get("vendor"):
                    fields["vendor"] = llm_fields["vendor"]
                if fields["amount"] is None and llm_fields.get("amount") is not None:
                    try:
                        fields["amount"] = float(llm_fields["amount"])
                    except (ValueError, TypeError):
                        pass
                if not fields["date"] and llm_fields.get("date"):
                    fields["date"] = llm_fields["date"]
                if not fields["tax_id"] and llm_fields.get("tax_id"):
                    fields["tax_id"] = llm_fields["tax_id"]
                if not fields["line_items"] and llm_fields.get("line_items"):
                    fields["line_items"] = llm_fields["line_items"]

                # Recalculate confidence after LLM augmentation
                fields["confidence"] = _calculate_extraction_confidence(fields)
        except Exception as e:
            logger.warning("LLM fallback extraction failed: %s", e)

    return fields


def extract_call_journey_from_text(text: str) -> Dict[str, Any]:
    """
    Extract outbound call blocks and milestone elapsed times from OCR text.
    Handles OCR character confusion (e.g. o/O -> 0, l/1/i/| -> l) and strips noise.
    Matches the user reference specification for call journey validation.
    """
    clean_text = text.lower()
    for ch in [" ", "@", "©", ">", "\n", "\t", '"', "'", "`", "~", "*", "_"]:
        clean_text = clean_text.replace(ch, "")

    # Error-tolerant call regex matching
    calls = re.findall(r"c[a4o0@][l1i\|]{2}|cal[l1i\|]|ca[l1i\|]l|call", clean_text)

    # Error-tolerant elapsed time pattern ([days]d [hours]h [mins]m)
    # Allows [hHn] for hour glyphs and [oO] for zeros
    time_pattern = re.compile(r"([0-9oO]+d)?([0-9oO]+)[hHn]([0-9oO]+)[mM]")
    raw_times = time_pattern.findall(clean_text)

    times = []
    for days, hours, mins in raw_times:
        days_str = days.replace("o", "0").replace("O", "0") if days else ""
        hours_str = hours.replace("o", "0").replace("O", "0")
        mins_str = mins.replace("o", "0").replace("O", "0")

        t = f"{days_str[:-1]}d {hours_str}h {mins_str}m" if days_str else f"{hours_str}h {mins_str}m"
        times.append(t)

    # Remove duplicates preserving order
    unique_times = list(dict.fromkeys(times))

    journey_steps = []
    for i, t in enumerate(unique_times):
        step = {"call_index": i + 1, "timestamp": t}
        if i < len(unique_times) - 1:
            step["next_step_after"] = unique_times[i + 1]
        journey_steps.append(step)

    return {
        "call_count": len(calls),
        "times": unique_times,
        "journey": journey_steps,
        "cleaned_text": clean_text,
    }
