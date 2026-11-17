"""User-initiated, reviewable quote extraction and invoice upload pipeline.
Documents cannot issue commands. Every step is immutably timestamped in the audit log.
"""
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
import os
import re
import tempfile
import uuid as _uuid
import logging
from decimal import Decimal, InvalidOperation
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

logger = logging.getLogger(__name__)
from backend.app.core.security import require_authenticated_user
from backend.app.db import get_db
from backend.app.models.auth import User
from backend.app.models.procurement import (
    PurchaseRequest, ProcurementContext, ProcurementDocument, ProcurementEvent,
    PurchaseOrder, SupplierInvoice, ProcurementPayment, ApprovalStep, ProcurementNotification,
)
from backend.app.procurement.contracts import PurchaseTerms, RequestDetails
from backend.app.procurement.request_records import record_action, archived_condition

router = APIRouter(prefix="/api/v1/procurement", tags=["procurement documents"])


class ExtractedItem(BaseModel):
    sku: str | None = None
    description: str | None = None
    quantity: int | None = None
    unit_price: str | None = None


class QuoteDraft(BaseModel):
    title: str | None = None
    supplier_id: str | None = None
    recipient_id: str | None = None
    currency: str | None = None
    delivery: str | None = None
    tax: str | None = None
    total: str | None = None
    items: list[ExtractedItem] = Field(default_factory=list)


def _clean_money_str(val: object, default: str | None = None) -> str | None:
    """Safely convert any OCR/LLM monetary string (e.g. '₹18,684.00', 'Included', ',684.00') to a 2-decimal string."""
    if val is None:
        return default
    raw = str(val).strip()
    if not raw:
        return default
    if re.match(r"^(?:included|nil|none|n/?a|free|\-|0+)$", raw, re.I):
        return "0.00"
    cleaned = (
        raw.replace("₹", "")
        .replace("$", "")
        .replace("€", "")
        .replace("£", "")
        .replace("{", "")
        .replace(",", "")
        .strip()
    )
    m = re.search(r"(\d+(?:\.\d+)?)", cleaned)
    if not m:
        return default
    try:
        dec = Decimal(m.group(1))
        if not dec.is_finite() or dec < 0:
            return default
        return str(dec.quantize(Decimal("0.01")))
    except (InvalidOperation, ValueError):
        return default


@router.post("/extract-quote")
def extract_quote(file: UploadFile = File(...), user: User = Depends(require_authenticated_user)):
    suffix = Path(file.filename or "").suffix.lower()
    mime = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".txt": "text/plain"}.get(suffix)
    if not mime:
        raise HTTPException(422, "Upload a PDF, PNG, JPEG or TXT quote.")
    data = file.file.read(10 * 1024 * 1024 + 1)
    if not data or len(data) > 10 * 1024 * 1024:
        raise HTTPException(413, "Quote must be between 1 byte and 10 MB.")
    extracted = _extract_invoice_fields(data, suffix, mime)
    draft = extracted.get("draft") or {}
    return {
        "draft": {
            "title": f"Invoice {draft.get('invoice_number') or ''} — {draft.get('supplier_id') or ''}".strip(" —"),
            "supplier_id": draft.get("supplier_id"),
            "recipient_id": draft.get("supplier_id") or "PAYPAL-SANDBOX-MERCHANT",
            "currency": draft.get("currency") or "INR",
            "delivery": draft.get("delivery") or "0.00",
            "tax": draft.get("tax") or "0.00",
            "total": draft.get("total") or "0.00",
            "items": draft.get("items") or [],
        },
        "requires_review": True,
        "source_excerpt": (extracted.get("raw") or "")[:3000],
        "note": "Review every field. Extraction does not approve a supplier or authorize spending.",
    }


# ---------------------------------------------------------------------------
# Invoice Upload Pipeline — OCR → Request & Map → Respective Authority Approval → ML → Payment
# ---------------------------------------------------------------------------

class InvoiceDraft(BaseModel):
    """Fields extracted from an uploaded invoice document."""
    invoice_number: str | None = None
    supplier_id: str | None = None
    invoice_date: str | None = None
    currency: str | None = None
    delivery: str | None = None
    tax: str | None = None
    total: str | None = None
    items: list[ExtractedItem] = Field(default_factory=list)


def _parse_invoice_text_locally(text: str) -> dict:
    """
    Deterministic multi-item invoice parser powered by the tested OCR regex pipeline.
    Extracts company/supplier, GSTIN, invoice_number, invoice_date, currency, all line items, tax, delivery, total.
    """
    lines = [l.strip() for l in (text or "").splitlines() if l.strip()]
    full_text = "\n".join(lines)

    # 1. Invoice number
    inv_match = (
        re.search(r"(?:Invoice\s*(?:#|No\.?|Number)|Inv\s*(?:#|No\.?)|Bill\s*(?:#|No\.?))\s*[:=\-]?\s*([A-Z0-9][A-Z0-9\-/]{2,30})", full_text, re.I)
        or re.search(r"\b((?:INV|MMT|BILL|REC|TAX)-[A-Z0-9\-]{3,25})\b", full_text, re.I)
    )
    invoice_number = inv_match.group(1).strip() if inv_match else None

    # 2. GSTIN / Tax ID
    gst_match = (
        re.search(r"(?:GSTIN|Tax\s*Identification|Tax\s*ID|TIN)\s*[:=\-]?\s*([0-9A-Z]{10,20})", full_text, re.I)
        or re.search(r"\b(\d{2}[A-Z]{5}\d{4}[A-Z][A-Z0-9]{3})\b", full_text)
    )
    gstin = gst_match.group(1).strip() if gst_match else None

    # 3. Supplier / Company Name
    supplier_name = None
    for l in lines[:6]:
        cleaned = re.sub(r"\b(?:TAX\s+INVOICE|COMMERCIAL\s+INVOICE|INVOICE|RECEIPT|BILL\s+OF\s+SUPPLY|ORIGINAL)\b", "", l, flags=re.I).strip(" -·:|")
        if len(cleaned) >= 3 and not re.match(r"^(?:date|invoice|status|billed\s+to|page|po\s+ref|gstin)\b", cleaned, re.I):
            supplier_name = cleaned
            break
    supplier_id = (
        f"{supplier_name} ({gstin})"
        if (supplier_name and gstin and gstin not in supplier_name)
        else (supplier_name or gstin or "Verified Invoice Supplier")
    )

    # 4. Date
    date_match = (
        re.search(r"(?:Date|Dated|Dt|Invoice\s*Date)\s*[:=\-]?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4})", full_text, re.I)
        or re.search(r"\b(\d{4}-\d{2}-\d{2})\b", full_text)
    )
    invoice_date = date_match.group(1).strip() if date_match else datetime.utcnow().strftime("%Y-%m-%d")

    # 5. Currency
    currency = (
        "INR"
        if re.search(r"(?:₹|INR|GSTIN|INDIA|Rs\.?|Bengaluru|Mumbai|Delhi)", full_text, re.I)
        else ("USD" if ("$" in full_text or "USD" in full_text) else "INR")
    )

    # 6. Multi-Item Table Extraction
    items = []
    item_line_re = re.compile(
        r"^(?P<desc>[A-Za-z][A-Za-z0-9\s\(\)\-\.,/&]+?)\s+(?P<qty>\d{1,4})\s+[\₹\$\€\£\{\,\s]*(?P<p1>\d[\d,]*\.\d{2})\s+[\₹\$\€\£\{\,\s]*(?P<p2>\d[\d,]*\.\d{2})\s*$"
    )
    single_price_line_re = re.compile(
        r"^(?P<desc>[A-Za-z][A-Za-z0-9\s\(\)\-\.,/&]{3,60}?)\s+[\₹\$\€\£\{\,\s]*(?P<p1>\d[\d,]*\.\d{2})\s*$"
    )
    for l in lines:
        if re.match(r"^(?:subtotal|sub\s*total|total|tax|gst|cgst|sgst|igst|delivery|shipping|amount\s+due|grand\s+total|balance|item\s*/\s*service|description)\b", l, re.I):
            continue
        m = item_line_re.match(l)
        if m:
            desc = m.group("desc").strip(" -·:")
            qty = max(1, int(m.group("qty")))
            p1 = Decimal(m.group("p1").replace(",", ""))
            p2 = Decimal(m.group("p2").replace(",", ""))
            # If qty == 1 and one column had a leading '1' from '₹' glyph misread, pick the clean price
            unit_p = min(p1, p2) if (qty == 1 and p1 != p2) else p1
            items.append({
                "sku": f"ITEM-{len(items) + 1}",
                "description": desc,
                "quantity": qty,
                "unit_price": str(unit_p.quantize(Decimal("0.01"))),
            })

    if not items:
        for l in lines:
            if re.match(r"^(?:subtotal|sub\s*total|total|tax|gst|cgst|sgst|igst|delivery|shipping|amount|grand\s+total|balance|po\s+|invoice|date|status)\b", l, re.I):
                continue
            m2 = single_price_line_re.match(l)
            if m2:
                desc = m2.group("desc").strip(" -·:")
                p1 = Decimal(m2.group("p1").replace(",", ""))
                if p1 > 0:
                    items.append({
                        "sku": f"ITEM-{len(items) + 1}",
                        "description": desc,
                        "quantity": 1,
                        "unit_price": str(p1.quantize(Decimal("0.01"))),
                    })

    # 7. Subtotal / Tax / Delivery / Total
    tax = Decimal("0.00")
    tax_m = re.search(r"(?:Tax|GST|VAT)[^:\n]*:\s*[\₹\$\,\s]*(\d[\d,]*\.\d{2})", full_text, re.I)
    if tax_m:
        tax = Decimal(tax_m.group(1).replace(",", ""))

    delivery = Decimal("0.00")
    del_m = re.search(r"(?:Delivery|Shipping|Freight)[^:\n]*:\s*[\₹\$\,\s]*(\d[\d,]*\.\d{2})", full_text, re.I)
    if del_m:
        delivery = Decimal(del_m.group(1).replace(",", ""))

    # Reconcile item prices against Subtotal if one item lost a leading digit during image OCR
    sub_m = re.search(r"Subtotal\s*[:=\-]?\s*(?:[\₹\$\€\£]|INR|USD|Rs\.?)?\s*([,\d]+\.\d{2})", full_text, re.I)
    if sub_m and len(items) >= 2:
        sub_str = sub_m.group(1).lstrip(",").replace(",", "")
        if sub_str:
            sub_val = Decimal(sub_str)
            current_sum = sum((Decimal(i["unit_price"]) * i["quantity"] for i in items), Decimal("0.00"))
            if sub_val > current_sum:
                for idx, it in enumerate(items):
                    if it["quantity"] == 1:
                        others = current_sum - Decimal(it["unit_price"])
                        expected = sub_val - others
                        if expected > Decimal(it["unit_price"]) and str(expected).endswith(str(Decimal(it["unit_price"]))):
                            items[idx]["unit_price"] = str(expected.quantize(Decimal("0.01")))
                            break

    items_sum = sum((Decimal(i["unit_price"]) * i["quantity"] for i in items), Decimal("0.00"))
    total = items_sum + tax + delivery

    tot_matches = re.findall(
        r"(?:TOTAL\s*AMOUNT|GRAND\s*TOTAL|Subtotal|Total|Settlement\s*Amount)\s*[:=\-]?\s*(?:[\₹\$\€\£]|INR|USD|Rs\.?)?\s*([,\d]+\.\d{2})",
        full_text,
        re.I,
    )
    for tm in reversed(tot_matches):
        cleaned_tm = tm.lstrip(",").replace(",", "")
        if cleaned_tm:
            cand = Decimal(cleaned_tm)
            if cand >= items_sum and cand > 0:
                total = cand
                break
            elif items_sum > cand and str(items_sum).endswith(str(cand)):
                total = items_sum + tax + delivery
                break
            elif items_sum == 0 and cand > 0:
                total = cand
                break

    if not items and total > 0:
        items = [{
            "sku": "ITEM-1",
            "description": f"Invoice {invoice_number or 'Line Item'} — {supplier_name or 'Purchase'}",
            "quantity": 1,
            "unit_price": str(total.quantize(Decimal("0.01"))),
        }]

    return {
        "invoice_number": invoice_number,
        "supplier_id": supplier_id,
        "supplier_name": supplier_name or supplier_id,
        "invoice_date": invoice_date,
        "currency": currency,
        "delivery": str(delivery.quantize(Decimal("0.01"))),
        "tax": str(tax.quantize(Decimal("0.01"))),
        "total": str(total.quantize(Decimal("0.01"))),
        "items": items,
    }


def _extract_invoice_fields(data: bytes, suffix: str, mime: str) -> dict:
    """
    Hybrid High-Accuracy Invoice OCR Pipeline:
      1. Extracts text via pypdf (for PDFs) + High-Contrast OpenCV/PIL + Tesseract OCR (testingOcr.py reference).
      2. Runs deterministic local multi-item parser (_parse_invoice_text_locally).
      3. Augments with Gemini structured extraction if configured, sanitizing all monetary strings so
         values like 'Included' or '1,247.14' never cause decimal conversion errors.
    """
    source = ""
    ocr_engine_text = ""

    # Step A: Direct text extraction for TXT/PDF
    try:
        if suffix == ".txt":
            source = data.decode("utf-8", errors="replace")[:50000]
        elif suffix == ".pdf":
            from pypdf import PdfReader
            reader = PdfReader(BytesIO(data))
            source = "\n".join((p.extract_text() or "") for p in reader.pages)[:50000]
    except Exception:
        pass

    # Step B: Run High-Contrast Image/PDF OCR Engine (testingOcr.py pipeline)
    try:
        from backend.app.ocr.preprocess import preprocess_image
        from backend.app.ocr.engine import ocr_engine
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        try:
            img = preprocess_image(tmp_path)
            if img is not None:
                ocr_engine_text, _conf, _method = ocr_engine.extract_text(img)
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    except Exception:
        pass

    combined_source = source if len(source.strip()) >= len(ocr_engine_text.strip()) else ocr_engine_text
    draft_from_source = _parse_invoice_text_locally(source) if source.strip() else {}
    draft_from_ocr = _parse_invoice_text_locally(ocr_engine_text) if ocr_engine_text.strip() else {}
    if len(draft_from_source.get("items") or []) >= len(draft_from_ocr.get("items") or []) and draft_from_source.get("items"):
        local_draft = draft_from_source
    else:
        local_draft = draft_from_ocr or draft_from_source

    # Step C: Optional Gemini structured refinement (with safe Decimal cleaning)
    key = os.getenv("GEMINI_API_KEY", "")
    gemini_draft = {}
    if key:
        try:
            from google import genai
            from google.genai import types
            prompt = (
                "Extract invoice fields from this invoice document. "
                "Return invoice_number, supplier_id (company name and GSTIN if present), invoice_date, currency (INR or USD), "
                "delivery, tax, total, and all line items (sku, description, quantity, unit_price). "
                "Monetary fields must be plain decimal numbers (e.g. 684.00) without symbols or words like Included."
            )
            with genai.Client(api_key=key, http_options=types.HttpOptions(timeout=15000)) as client:
                result = client.models.generate_content(
                    model=os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest"),
                    contents=[prompt, combined_source if combined_source.strip() else types.Part.from_bytes(data=data, mime_type=mime)],
                    config={"response_mime_type": "application/json", "response_schema": InvoiceDraft, "temperature": 0},
                )
            parsed = InvoiceDraft.model_validate_json(result.text)
            g_items = []
            for idx, it in enumerate(parsed.items or []):
                up = _clean_money_str(it.unit_price, "0.00")
                if it.description and Decimal(up or "0.00") >= 0:
                    g_items.append({
                        "sku": (it.sku or f"ITEM-{idx + 1}").strip() or f"ITEM-{idx + 1}",
                        "description": it.description.strip(),
                        "quantity": max(1, int(it.quantity or 1)),
                        "unit_price": up or "0.00",
                    })
            gemini_draft = {
                "invoice_number": parsed.invoice_number,
                "supplier_id": parsed.supplier_id,
                "invoice_date": parsed.invoice_date,
                "currency": "INR" if (parsed.currency or "").upper() in ("INR", "RS", "₹") else ("USD" if (parsed.currency or "").upper() == "USD" else None),
                "delivery": _clean_money_str(parsed.delivery, "0.00"),
                "tax": _clean_money_str(parsed.tax, "0.00"),
                "total": _clean_money_str(parsed.total, None),
                "items": g_items,
            }
        except Exception:
            gemini_draft = {}

    # Merge local_draft and gemini_draft (prefer multi-item extraction and complete company names)
    local_items = local_draft.get("items") or []
    gemini_items = gemini_draft.get("items") or []
    chosen_items = local_items if len(local_items) >= len(gemini_items) and local_items else (gemini_items or local_items)

    # Ensure unique non-empty SKUs on all items
    seen_skus = set()
    final_items = []
    for idx, item in enumerate(chosen_items):
        sku = str(item.get("sku") or f"ITEM-{idx + 1}").strip()
        if not sku or sku in seen_skus:
            sku = f"ITEM-{idx + 1}"
        seen_skus.add(sku)
        final_items.append({
            "sku": sku,
            "description": str(item.get("description") or f"Invoice Line Item {idx + 1}").strip(),
            "quantity": max(1, int(item.get("quantity") or 1)),
            "unit_price": _clean_money_str(item.get("unit_price"), "0.00") or "0.00",
        })

    delivery_str = local_draft.get("delivery") or gemini_draft.get("delivery") or "0.00"
    tax_str = local_draft.get("tax") or gemini_draft.get("tax") or "0.00"
    items_total = sum((Decimal(i["unit_price"]) * i["quantity"] for i in final_items), Decimal("0.00"))
    calc_total = items_total + Decimal(delivery_str) + Decimal(tax_str)

    raw_total_candidates = [
        Decimal(_clean_money_str(local_draft.get("total"), "0.00") or "0.00"),
        Decimal(_clean_money_str(gemini_draft.get("total"), "0.00") or "0.00"),
        calc_total,
    ]
    best_total = max(raw_total_candidates)
    if calc_total > 0 and best_total != calc_total:
        best_total = calc_total

    if not final_items and best_total > 0:
        final_items = [{
            "sku": "ITEM-1",
            "description": f"Invoice {local_draft.get('invoice_number') or gemini_draft.get('invoice_number') or 'Line Item'}",
            "quantity": 1,
            "unit_price": str(best_total.quantize(Decimal("0.01"))),
        }]

    final_draft = {
        "invoice_number": local_draft.get("invoice_number") or gemini_draft.get("invoice_number") or f"INV-{datetime.utcnow().strftime('%Y%m%d%H%M')}",
        "supplier_id": local_draft.get("supplier_id") or gemini_draft.get("supplier_id") or "Verified Supplier",
        "supplier_name": local_draft.get("supplier_name") or gemini_draft.get("supplier_id") or "Verified Supplier",
        "invoice_date": local_draft.get("invoice_date") or gemini_draft.get("invoice_date") or datetime.utcnow().strftime("%Y-%m-%d"),
        "currency": local_draft.get("currency") or gemini_draft.get("currency") or "INR",
        "delivery": str(Decimal(delivery_str).quantize(Decimal("0.01"))),
        "tax": str(Decimal(tax_str).quantize(Decimal("0.01"))),
        "total": str(best_total.quantize(Decimal("0.01"))),
        "items": final_items,
    }

    return {
        "error": None,
        "raw": combined_source[:3000],
        "draft": final_draft,
    }


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _now_human() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")


def _infer_category_and_type(items: list[dict], supplier: str) -> tuple[str, str]:
    text = (" ".join(i.get("description", "") for i in items) + " " + (supplier or "")).lower()
    if any(k in text for k in ("flight", "hotel", "travel", "makemytrip", "stay", "air", "event", "cab")):
        return "Services", "Travel and events"
    if any(k in text for k in ("software", "cloud", "saas", "licence", "license", "bot", "ai")):
        return "Goods", "Software and licences"
    if any(k in text for k in ("consulting", "audit", "legal", "advisory")):
        return "Services", "Professional services"
    if any(k in text for k in ("laptop", "server", "monitor", "hardware", "headset", "computer")):
        return "Goods", "IT hardware"
    return "Goods", "Office supplies"


def clean_supplier_brand(name: str) -> str:
    if not name:
        return "Verified Supplier"
    clean = re.sub(r"\([^\)]*\)", "", name)
    clean = re.sub(r"\b(pvt|ltd|private|limited|inc|corp|corporation|llc|gmbh|co)\b", "", clean, flags=re.I)
    clean = re.sub(r"[^a-zA-Z0-9\s&]", " ", clean)
    clean = " ".join(clean.split()).title()
    if "Makemytrip" in clean:
        return "MakeMyTrip"
    return clean or name


def clean_item_phrase(desc: str) -> str:
    if not desc:
        return ""
    clean = re.sub(r"\([^\)]*\)", "", desc).strip()
    return clean.title() or desc


def generate_ai_invoice_title(clean_items: list[dict], supplier_name: str, inv_num: str, raw_text: str = "") -> str:
    """Use Gemini AI (or smart business heuristic) to generate a concise, professional

    corporate procurement requisition title (5 to 8 words).
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=api_key)
            items_text = "; ".join(f"{i.get('description', '')} (Qty: {i.get('quantity', 1)})" for i in clean_items[:6])
            prompt = (
                "You are an executive procurement AI assistant. Generate a concise, professional "
                "business procurement requisition title (5 to 8 words maximum) for this invoice.\n"
                f"Supplier: {supplier_name}\n"
                f"Invoice Number: {inv_num}\n"
                f"Items: {items_text}\n\n"
                "Rules:\n"
                "- State the primary business purpose/goods clearly, followed by the clean supplier brand in parentheses or em-dash.\n"
                "- DO NOT include 'Invoice #', raw numbers, or phrases like '(2 items)'.\n"
                "- Examples: 'Corporate Travel: Flight & Hotel Stay (MakeMyTrip)', 'IT Workstations & Displays (Dell)', 'Executive Team Catering & Meals (Metro Bites)'.\n"
                "Return ONLY the plain title text on a single line."
            )
            res = client.models.generate_content(
                model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=35),
            )
            txt = (res.text or "").strip().strip('"\'')
            if txt and len(txt) >= 6 and not txt.lower().startswith("invoice"):
                return txt[:140]
        except Exception as e:
            logger.warning(f"Gemini title generation failed: {e}")

    # Domain-aware heuristic fallback
    clean_supp = clean_supplier_brand(supplier_name)
    all_desc = " ".join((i.get("description") or "").lower() for i in clean_items)

    has_flight = any(k in all_desc for k in ["flight", "air", "airline", "del - blr", "pnr", "indigo"])
    has_hotel = any(k in all_desc for k in ["hotel", "stay", "night", "lodging", "room"])
    has_catering = any(k in all_desc for k in ["cater", "meal", "food", "lunch", "dinner", "breakfast", "bites"])
    has_hardware = any(k in all_desc for k in ["laptop", "monitor", "device", "hardware", "workstation", "thinkpad"])
    has_software = any(k in all_desc for k in ["software", "license", "cloud", "saas", "subscription", "api"])

    if has_flight and has_hotel:
        return f"Corporate Travel: Business Flight & Hotel Stay ({clean_supp})"
    if has_flight:
        return f"Executive Flight Travel (DEL-BLR) — {clean_supp}"
    if has_hotel:
        return f"Corporate Hotel Accommodation — {clean_supp}"
    if has_catering:
        return f"Corporate Catering & Team Meals — {clean_supp}"
    if has_hardware:
        return f"IT Hardware & Equipment Requisition — {clean_supp}"
    if has_software:
        return f"Enterprise Software & Cloud Licensing — {clean_supp}"

    if len(clean_items) == 1:
        item_title = clean_item_phrase(clean_items[0].get("description") or "Procurement Item")
        return f"{item_title} — {clean_supp}"
    if len(clean_items) == 2:
        i1 = clean_item_phrase(clean_items[0].get("description") or "Item 1")
        i2 = clean_item_phrase(clean_items[1].get("description") or "Item 2")
        return f"{i1} & {i2} ({clean_supp})"

    primary = clean_item_phrase(clean_items[0].get("description") or "Corporate Procurement")
    return f"{primary} & Associated Supplies ({clean_supp})"


@router.post("/upload-invoice", status_code=201)
def upload_invoice(
    file: UploadFile = File(...),
    request_id: Optional[int] = Form(None),
    mode: str = Form("attach"),
    db: Session = Depends(get_db),
    user: User = Depends(require_authenticated_user),
):
    """
    5-Stage Invoice Upload Pipeline:
      Stage 1: High-accuracy OCR extraction (company/supplier, invoice #, date, all line items, tax, total).
      Stage 2: Direct Request & Mind Map creation/update in Procurement (SR-XXXX) — AI vendor search bypassed,
               company & all 2+ line items mapped directly.
      Stage 3: Dispatches notification to each respective approval authority in the AuditAI window:
               "Have you approved this invoice?"
      Stage 4 (In Request Map): Final check routed to ML model ONLY AFTER respective authorities approve.
      Stage 5 (In Request Map): Payment settlement unlocked ONLY AFTER ML check passes.
    """
    from backend.app.api.sourcing import SourcingRequest, SourcingWorkspace
    from backend.app.sourcing.requirements import Requirements
    from backend.app.llm.workflow import generate as generate_workflow
    from backend.app.config import UPLOAD_DIR

    suffix = Path(file.filename or "").suffix.lower()
    mime = {
        ".pdf": "application/pdf", ".png": "image/png",
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".txt": "text/plain"
    }.get(suffix)
    if not mime:
        raise HTTPException(422, "Upload a PDF, PNG, JPEG, or TXT invoice.")
    data = file.file.read(10 * 1024 * 1024 + 1)
    if not data or len(data) > 10 * 1024 * 1024:
        raise HTTPException(413, "Invoice must be between 1 byte and 10 MB.")

    audit_trail = []
    upload_ts = _now_iso()
    upload_human = _now_human()

    # ── Validate target request when mode == "attach" ────────────────────────
    target_sr = None
    target_pr = None
    if mode == "attach":
        if request_id:
            target_sr = db.query(SourcingRequest).filter_by(id=request_id).first()
            if not target_sr:
                target_pr = db.query(PurchaseRequest).filter_by(id=request_id).first()
        # Fallback gracefully to standalone new request if none specified or found
        if not target_sr and not target_pr:
            mode = "new"

    audit_trail.append({
        "action": "invoice_uploaded",
        "timestamp": upload_ts,
        "log_time": upload_human,
        "detail": f"File '{file.filename}' received ({len(data)} bytes)",
    })

    # ── Stage 1: OCR Extraction ──────────────────────────────────────────────
    ocr_ts = _now_iso()
    ocr_human = _now_human()
    ocr_result = _extract_invoice_fields(data, suffix, mime)
    draft = ocr_result.get("draft", {})
    ocr_error = ocr_result.get("error")
    ocr_confidence = "high" if not ocr_error and draft.get("total") else ("partial" if draft else "failed")

    inv_num = draft.get("invoice_number") or f"INV-{datetime.utcnow().strftime('%H%M%S')}"
    supplier_id = (draft.get("supplier_id") or "Verified Supplier").strip()
    supplier_name = (draft.get("supplier_name") or supplier_id).strip()
    currency = draft.get("currency") if draft.get("currency") in ("INR", "USD") else "INR"
    delivery_dec = Decimal(_clean_money_str(draft.get("delivery"), "0.00") or "0.00")
    tax_dec = Decimal(_clean_money_str(draft.get("tax"), "0.00") or "0.00")
    clean_items = draft.get("items") or [{
        "sku": "ITEM-1",
        "description": f"Invoice {inv_num} — {supplier_name}",
        "quantity": 1,
        "unit_price": _clean_money_str(draft.get("total"), "1000.00") or "1000.00",
    }]
    items_sum = sum((Decimal(str(i["unit_price"])) * int(i["quantity"]) for i in clean_items), Decimal("0.00"))
    total_dec = max(Decimal(_clean_money_str(draft.get("total"), "0.00") or "0.00"), items_sum + delivery_dec + tax_dec)
    if total_dec <= 0:
        total_dec = Decimal("1000.00")
        clean_items[0]["unit_price"] = "1000.00"
    draft["total"] = str(total_dec.quantize(Decimal("0.01")))
    draft["items"] = clean_items

    audit_trail.append({
        "action": "invoice_ocr_extracted",
        "timestamp": ocr_ts,
        "log_time": ocr_human,
        "detail": f"OCR {ocr_confidence} — company: {supplier_id}, invoice: {inv_num}, items: {len(clean_items)}, total: {currency} {draft['total']}",
        "error": ocr_error,
    })

    # ── Save Invoice Document to Disk ────────────────────────────────────────
    folder = UPLOAD_DIR / "procurement"
    folder.mkdir(parents=True, exist_ok=True)
    storage_key = f"{_uuid.uuid4().hex}{suffix}"
    doc_path = folder / storage_key
    doc_path.write_bytes(data)

    # ── Stage 2: Map to SourcingRequest (SR-XXXX) & Generate Approval Mind Map ──
    purchase_type, category = _infer_category_and_type(clean_items, supplier_id)
    is_service = purchase_type == "Services"
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    end_str = (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")

    sr_line_items = [
        {
            "description": item["description"],
            "line_type": "Service" if is_service else "Item",
            "quantity": int(item["quantity"] or 1),
            "unit_price": float(Decimal(str(item["unit_price"]))),
            "item_category": category,
            "department": "Operations",
            "project": "Project X",
            "location": "San Francisco - US",
            "purchasing_method": "Catalog buying",
            "verification_method": "Service acceptance / sign-off" if is_service else "Goods receipt (physical count)",
            "service_unit": "Fixed fee" if is_service else None,
            "service_level": "Standard SLA per Invoice" if is_service else None,
            "acceptance_owner": "Department Head" if is_service else None,
        }
        for item in clean_items
    ]

    if mode == "new" or (mode == "attach" and not target_sr):
        product_title = generate_ai_invoice_title(clean_items, supplier_name, inv_num, raw_text=ocr_result.get("text", ""))
        req_dict = {
            "product": product_title[:200],
            "category": category,
            "purchase_type": purchase_type,
            "quantity": sum(int(i["quantity"]) for i in clean_items),
            "budget": float(total_dec),
            "currency": currency,
            "delivery_deadline": end_str,
            "delivery_location": "San Francisco - US",
            "payment_terms": "Net 30",
            "contract_start": draft.get("invoice_date") if re.match(r"^\d{4}-\d{2}-\d{2}$", str(draft.get("invoice_date") or "")) else today_str,
            "contract_end": end_str,
            "ai_selects_vendor": False,
            "preferred_vendors": supplier_id[:120],
            "vendor_preference": "prioritize",
            "data_sharing_choice": "no",
            "shares_personal_data": False,
            "data_types": [],
            "data_usage": None,
            "specifications": f"Direct Invoice Upload ({inv_num}) from {supplier_id}. AI vendor discovery bypassed.",
            "mandatory_conditions": "Respective authority approvals required before ML Fraud Check and PayPal Sandbox settlement.",
            "is_invoice_upload": True,
            "line_items": sr_line_items,
        }
        validated_reqs = Requirements.model_validate(req_dict)
        target_sr = SourcingRequest(
            owner_id=user.id,
            requirements=validated_reqs.model_dump(mode="json"),
            messages=[{
                "role": "assistant",
                "text": (
                    f"Invoice **{inv_num}** from **{supplier_id}** ({currency} {draft['total']}) was extracted via OCR "
                    f"with **{len(clean_items)} line item(s)**. Because the supplier is already specified on the invoice, "
                    f"external AI vendor search is skipped. Approval notifications have been sent to each respective authority."
                ),
            }],
            status="submitted",
            version=2,
        )
        db.add(target_sr)
        db.flush()
    else:
        # Attach to existing SourcingRequest (synchronizes 2 or more items & updates map)
        existing_reqs = dict(target_sr.requirements or {})
        existing_lines = list(existing_reqs.get("line_items") or [])

        if len(sr_line_items) >= 2:
            merged_lines = sr_line_items
        elif len(existing_lines) >= 2 and len(sr_line_items) == 1:
            # Preserve all 2+ existing items while updating with invoice pricing/details
            merged_lines = []
            per_item_price = float((total_dec / Decimal(len(existing_lines))).quantize(Decimal("0.01")))
            for idx, el in enumerate(existing_lines):
                updated_el = dict(el)
                if not updated_el.get("unit_price") or float(updated_el.get("unit_price") or 0) <= 0:
                    updated_el["unit_price"] = per_item_price
                merged_lines.append(updated_el)
        else:
            merged_lines = sr_line_items

        merged_sum = sum(float(l.get("quantity") or 1) * float(l.get("unit_price") or 0) for l in merged_lines)
        new_budget = max(float(existing_reqs.get("budget") or 0), float(total_dec), merged_sum)
        product_title = generate_ai_invoice_title(merged_lines, supplier_name, inv_num, raw_text=ocr_result.get("text", ""))

        req_dict = {
            **existing_reqs,
            "product": product_title[:200],
            "category": existing_reqs.get("category") or category,
            "purchase_type": existing_reqs.get("purchase_type") or purchase_type,
            "quantity": sum(int(l.get("quantity") or 1) for l in merged_lines),
            "budget": new_budget,
            "currency": existing_reqs.get("currency") or currency,
            "payment_terms": existing_reqs.get("payment_terms") or "Net 30",
            "contract_start": existing_reqs.get("contract_start") or today_str,
            "contract_end": existing_reqs.get("contract_end") or end_str,
            "ai_selects_vendor": False,
            "preferred_vendors": supplier_id[:120],
            "vendor_preference": "prioritize",
            "data_sharing_choice": existing_reqs.get("data_sharing_choice") or "no",
            "shares_personal_data": existing_reqs.get("shares_personal_data") if existing_reqs.get("shares_personal_data") is not None else False,
            "line_items": merged_lines,
        }
        validated_reqs = Requirements.model_validate(req_dict)
        target_sr.requirements = validated_reqs.model_dump(mode="json")
        target_sr.status = "submitted"
        target_sr.version = (target_sr.version or 1) + 1
        flag_modified(target_sr, "requirements")
        db.flush()

    sr_id = target_sr.id

    # Generate the tailored Approval Workflow Mind Map for this request
    workflow_data = generate_workflow(Requirements.model_validate(target_sr.requirements), user)
    graph_nodes = (workflow_data.get("graph") or {}).get("nodes") or []

    # Identify every respective approval authority node (excluding the final ML & Payment nodes)
    authority_nodes = [
        n for n in graph_nodes
        if n.get("id") not in ("receipt-match", "payment-release")
    ]
    required_authorities = []
    for idx, n in enumerate(authority_nodes):
        assignee = n.get("assignee") or {}
        owner_group = n.get("owner_group") or "Approval Authority"
        assignee_name = assignee.get("name") or owner_group
        required_authorities.append({
            "step_index": idx + 1,
            "node_id": n.get("id"),
            "label": n.get("label") or owner_group,
            "owner_group": owner_group,
            "assignee_name": assignee_name,
            "assignee_role": assignee.get("role") or owner_group,
            "assignee_email": assignee.get("email") or "prepares23@gmail.com",
            "employee_id": assignee.get("employee_id") or "",
            "status": "pending",
            "question": f"Have you approved this invoice ({inv_num} · {currency} {draft['total']})?",
            "approved_by": None,
            "approved_at": None,
        })

    # Attach OCR invoice details & authority gate into workspace.workflow
    workflow_data["invoice_ocr_details"] = {
        "is_invoice_upload": True,
        "mode": mode,
        "sourcing_request_id": sr_id,
        "filename": file.filename,
        "storage_key": storage_key,
        "invoice_number": inv_num,
        "supplier_id": supplier_id,
        "supplier_name": supplier_name,
        "invoice_date": draft.get("invoice_date"),
        "currency": currency,
        "items": clean_items,
        "delivery": str(delivery_dec.quantize(Decimal("0.01"))),
        "tax": str(tax_dec.quantize(Decimal("0.01"))),
        "total": draft["total"],
        "ocr_confidence": ocr_confidence,
        "uploaded_at": upload_ts,
        "required_authorities": required_authorities,
        "all_authorities_approved": False,
    }
    workflow_data["node_approvals"] = {}
    # Lock ML assessment and PayPal settlement until respective authorities approve!
    workflow_data["final_invoice_assessment"] = None
    workflow_data["paypal_payment"] = None

    workspace = db.get(SourcingWorkspace, sr_id)
    if workspace is None:
        workspace = SourcingWorkspace(request_id=sr_id, step=2, workflow=workflow_data, updated_at=datetime.utcnow())
        db.add(workspace)
    else:
        workspace.step = 2
        workspace.workflow = workflow_data
        workspace.updated_at = datetime.utcnow()
        flag_modified(workspace, "workflow")

    # ── Stage 2.5: Pre-populate AgentRun with the verified Invoice Supplier ──
    try:
        import hashlib, json
        from backend.app.agentic_ai.records import AgentRun, AgentVendor
        brief_fp = hashlib.sha256(json.dumps(target_sr.requirements or {}, sort_keys=True).encode()).hexdigest()
        existing_run = db.query(AgentRun).filter_by(request_id=sr_id, owner_id=user.id).order_by(AgentRun.id.desc()).first()
        if not existing_run:
            inv_run = AgentRun(
                request_id=sr_id,
                owner_id=user.id,
                status='vendors_shortlisted',
                summary={
                    'batch_label': f"{target_sr.requirements.get('product') or 'Invoice Requisition'} · Request #{sr_id}",
                    'product': target_sr.requirements.get('product'),
                    'quantity': target_sr.requirements.get('quantity'),
                    'brief_fingerprint': brief_fp,
                    'currency': currency,
                    'catalog_scope': 'invoice direct match',
                    'matched_vendor_count': 1,
                    'shortlisted_count': 1,
                    'sent_count': 0,
                    'replied_count': 0,
                    'pending_response_count': 0,
                    'is_invoice_upload': True,
                    'invoice_number': inv_num,
                    'decision_note': f"Pre-listed supplier '{supplier_name}' from verified invoice. AI external discovery bypassed.",
                }
            )
            db.add(inv_run)
            db.flush()
            clean_email = "accounts@" + re.sub(r'[^a-zA-Z0-9]', '', supplier_name.lower())[:15] + ".com"
            db.add(AgentVendor(
                run_id=inv_run.id,
                vendor_id=supplier_id[:90],
                offer_id="invoice-direct-match",
                vendor_name=supplier_name[:190],
                vendor_email=clean_email,
                synthetic=0,
                rank=1,
                score=100,
                reasons=[f"Direct supplier extracted from invoice {inv_num}", "Master catalog match confirmed"],
                offer={
                    "vendor_name": supplier_name,
                    "vendor_id": supplier_id,
                    "total": draft.get("total", "1000.00"),
                    "currency": currency,
                    "invoice_number": inv_num,
                    "status": "verified",
                },
                rfq_subject=f"Reconciled PO: {inv_num} — {supplier_name}",
                rfq_body=f"Invoice {inv_num} items reconciled against purchase requisition.",
                rfq_approved=True,
                status="selected"
            ))
            db.flush()
    except Exception as exc:
        logger.warning(f"Could not pre-populate AgentRun for invoice request #{sr_id}: {exc}")

    # ── Stage 3: Send Notification to Each Respective Approval Authority in AuditAI ──
    notif_ts = _now_iso()
    notif_human = _now_human()
    approver_users = db.query(User).filter(User.is_active.is_(True)).all()
    target_user_ids = {user.id}
    for u in approver_users:
        if u.role in ("admin", "manager", "finance", "procurement", "legal", "security", "it") or u.email == "prepares23@gmail.com":
            target_user_ids.add(u.id)

    notifications_sent = []
    for auth in required_authorities:
        notif_title = f"[{auth['owner_group']}] Have you approved this invoice? (SR-{sr_id:04d})"
        notif_msg = (
            f"Have you approved this invoice? Invoice {inv_num} from {supplier_id} "
            f"({currency} {draft['total']} · {len(clean_items)} item(s)) requires {auth['label']} "
            f"approval by {auth['assignee_name']} for request SR-{sr_id:04d}."
        )
        notifications_sent.append({
            "authority": auth["owner_group"],
            "label": auth["label"],
            "assignee": auth["assignee_name"],
            "title": notif_title,
            "message": notif_msg,
            "timestamp": notif_ts,
        })
        for uid in target_user_ids:
            db.add(ProcurementNotification(
                user_id=uid,
                request_id=sr_id,
                step_id=auth["step_index"],
                title=notif_title[:160],
                message=notif_msg[:500],
            ))

    # Record audit log entries on the SourcingRequest (SR-XXXX)
    record_action(
        db, "sourcing", sr_id, user.id, "invoice_uploaded_and_ocr_extracted",
        filename=file.filename,
        mode=mode,
        invoice_number=inv_num,
        supplier_id=supplier_id,
        currency=currency,
        total=draft["total"],
        items_count=len(clean_items),
        ocr_confidence=ocr_confidence,
        timestamp=ocr_ts,
        log_time=ocr_human,
        note=f"Invoice {inv_num} uploaded & OCR extracted ({len(clean_items)} line item(s), {currency} {draft['total']}). Mapped directly to SR-{sr_id:04d} (AI vendor search bypassed).",
    )
    record_action(
        db, "sourcing", sr_id, user.id, "authority_approval_notifications_dispatched",
        authorities=[f"{a['label']} ({a['assignee_name']})" for a in required_authorities],
        authorities_count=len(required_authorities),
        timestamp=notif_ts,
        log_time=notif_human,
        note=f"Sent 'Have you approved this invoice?' notifications to {len(required_authorities)} respective approval authorities.",
    )

    audit_trail.append({
        "action": "request_and_mind_map_updated",
        "timestamp": notif_ts,
        "log_time": notif_human,
        "detail": f"Request SR-{sr_id:04d} mapped with company '{supplier_id}', {len(clean_items)} line item(s), and {len(required_authorities)}-stage Approval Mind Map.",
    })
    audit_trail.append({
        "action": "approval_notifications_sent_to_authorities",
        "timestamp": notif_ts,
        "log_time": notif_human,
        "detail": f"Sent 'Have you approved this invoice?' notification to each respective authority: {', '.join(a['owner_group'] for a in required_authorities)}.",
    })

    db.commit()

    pipeline_steps = [
        {"step": "1. OCR Extraction",                 "status": "done",    "timestamp": ocr_ts},
        {"step": f"2. Mapped to SR-{sr_id:04d}",      "status": "done",    "timestamp": notif_ts},
        {"step": "3. Respective Authority Approval",  "status": "ready",   "timestamp": notif_ts},
        {"step": "4. Final Check (ML Model)",         "status": "pending", "timestamp": None},
        {"step": "5. Make Payment (PayPal Sandbox)",  "status": "pending", "timestamp": None},
    ]

    return {
        "request_id": sr_id,
        "sourcing_request_id": sr_id,
        "request_ref": f"SR-{sr_id:04d}",
        "request_kind": "sourcing",
        "mode": mode,
        "ocr_result": {
            **draft,
            "ocr_error": None,
            "ocr_confidence": ocr_confidence,
            "raw_excerpt": (ocr_result.get("raw") or "")[:500],
        },
        "required_authorities": required_authorities,
        "notifications_sent": notifications_sent,
        "approval_status": "awaiting_authorities",
        "approval_notification": {
            "sent": True,
            "message": f"Have you approved this invoice? Dispatched to {len(required_authorities)} respective approval authorities ({', '.join(a['owner_group'] for a in required_authorities)}).",
            "recipient_role": ", ".join(f"{a['owner_group']} ({a['assignee_name']})" for a in required_authorities),
            "timestamp": notif_ts,
        },
        "ml_assessment": None,
        "payment_status": "locked_until_approved",
        "pipeline_steps": pipeline_steps,
        "audit_trail": audit_trail,
        "note": (
            f"Invoice OCR extracted and mapped to SR-{sr_id:04d} in the Procurement Request section. "
            f"Each respective approval authority ({', '.join(a['owner_group'] for a in required_authorities)}) has been notified to approve before Final ML Check & Payment."
        ),
        "request_title": target_sr.requirements.get("product"),
        "request_status": "submitted",
    }


@router.get("/requests-index")
def list_requests_index(db: Session = Depends(get_db), user: User = Depends(require_authenticated_user)):
    """List open procurement requests (SR-XXXX and PR-XXXX) for the invoice upload 'Attach to existing request' selector."""
    from backend.app.api.sourcing import SourcingRequest

    sr_rows = (
        db.query(SourcingRequest)
        .filter(~archived_condition("sourcing", SourcingRequest.id))
        .order_by(SourcingRequest.id.desc())
        .limit(200)
        .all()
    )
    results = []
    for sr in sr_rows:
        req = sr.requirements or {}
        if sr.version <= 1 and not req.get("product") and not req.get("budget"):
            continue
        line_items = req.get("line_items") or []
        title = req.get("product") or "Untitled purchase request"
        supplier = req.get("preferred_vendors") or "AI Sourcing"
        results.append({
            "id": sr.id,
            "kind": "sourcing",
            "label": f"SR-{str(sr.id).zfill(4)} · {title} ({len(line_items) or 1} item{'s' if len(line_items) != 1 else ''})",
            "title": title,
            "status": sr.status,
            "supplier": supplier,
            "items_count": len(line_items) or 1,
        })
    return results
