"""Prior-only behavioral features. Entity IDs are lookup keys, never inputs.

The expense application performs retrospective audits ordered by claimed date;
bulk-upload timestamps are not transaction timestamps. Offline records can use
an explicit event_time/availability timestamp. Equal timestamps cannot see one
another. Full ledger replay is deterministic and preserves caller row order.
"""
from collections import defaultdict, deque
from datetime import date, datetime
import math
import re

import numpy as np
import pandas as pd
from fuzzywuzzy import fuzz

from backend.app import config

FEATURE_NAMES = [
    'log_amount', 'is_negative', 'is_round', 'hour', 'weekend_flag',
    'is_holiday', 'is_after_hours', 'z_global', 'z_vendor', 'z_employee', 'z_category',
    'log_vendor_prior_n', 'log_employee_prior_n', 'vendor_is_new',
    'employee_is_new', 'pair_is_new', 'vendor_missing', 'employee_missing',
    'log_vendor_freq_30d', 'log_employee_freq_7d', 'log_days_since_vendor',
    'duplicate_prior', 'log_pair_amount_1d', 'log_pair_count_1d',
    'has_receipt', 'ocr_amount_missing', 'ocr_confidence',
    'ocr_confidence_missing', 'ocr_low_confidence', 'log_ocr_amount',
    'ocr_mismatch_ratio', 'ocr_vendor_mismatch', 'ocr_date_gap',
    'vendor_name_deviation',
]

# Policy calendar used by the model and the deterministic holiday review rule.
HOLIDAY_DATES = {
    pd.Timestamp(value, tz='UTC').date()
    for value in config.HOLIDAYS
}


def number(value, default=None):
    try:
        value = float(value)
        return value if math.isfinite(value) else default
    except (TypeError, ValueError):
        return default


def key(value):
    return '' if value is None or pd.isna(value) else str(value).strip().lower()


def event_time_info(claim):
    """Return a sortable UTC time and whether a real time of day was supplied."""
    value = claim.get('event_time') or claim.get('submitted_at')
    if value is None or pd.isna(value):
        value = claim.get('transaction_date', claim.get('claimed_date'))
        clock = claim.get('transaction_time')
        if clock is not None and not pd.isna(clock) and str(clock).strip():
            value = f"{value} {clock}"
    time_known = isinstance(value, datetime) or (
        not isinstance(value, date) and bool(re.search(r'[T ]\d{1,2}:\d{2}', str(value)))
    )
    ts = pd.to_datetime(value, errors='coerce', utc=True)
    if pd.isna(ts):
        raise ValueError('Every claim needs a valid event/submission date.')
    # A date-only record has no evidence about working hours. Noon is a
    # neutral ordering placeholder, never evidence of an after-hours event.
    return (ts if time_known else ts.normalize() + pd.Timedelta(hours=12)), time_known


def event_time(claim):
    return event_time_info(claim)[0]


def _ocr_features(c, amount):
    ocr = number(c.get('ocr_amount', c.get('ocr_extracted_amount')))
    confidence = number(c.get('ocr_confidence'))
    # Imported amounts with unknown quality remain explicitly marked unknown.
    usable = ocr is not None and (confidence is None or confidence >= config.OCR_MIN_CONFIDENCE)
    mismatch = min(abs(ocr - amount) / max(abs(amount), 1.0), 10) if usable else 0
    vendor = key(c.get('ocr_vendor'))
    actual_vendor = key(c.get('vendor_name'))
    gap = 0.0
    if usable and c.get('ocr_date'):
        a = pd.to_datetime(c.get('ocr_date'), errors='coerce', utc=True)
        b = pd.to_datetime(c.get('claimed_date', c.get('transaction_date')), errors='coerce', utc=True)
        if not pd.isna(a) and not pd.isna(b):
            gap = math.log1p(min(abs((a.normalize() - b.normalize()).days), 365))
    return dict(has_receipt=float(bool(c.get('has_receipt')) or ocr is not None),
                ocr_amount_missing=float(ocr is None),
                ocr_confidence=float(np.clip(confidence, 0, 1)) if confidence is not None else 0,
                ocr_confidence_missing=float(confidence is None),
                ocr_low_confidence=float(ocr is not None and not usable),
                log_ocr_amount=math.log1p(abs(ocr)) if usable else 0,
                ocr_mismatch_ratio=mismatch,
                ocr_vendor_mismatch=float(usable and bool(vendor) and bool(actual_vendor) and vendor != actual_vendor),
                ocr_date_gap=gap)


def compute_features_batch(claims, known_vendors=None):
    if not claims:
        return [], list(FEATURE_NAMES)
    time_info = [event_time_info(c) for c in claims]
    times = [time for time, _ in time_info]
    amounts = [number(c.get('claimed_amount', c.get('amount'))) for c in claims]
    if any(a is None for a in amounts):
        raise ValueError('Invalid or missing amounts must be corrected before model scoring.')
    stats = defaultdict(lambda: [0, 0.0, 0.0])
    windows = defaultdict(deque)
    last_vendor = {}
    output = [None] * len(claims)
    ordered = sorted(range(len(claims)), key=lambda i: times[i])

    def zscore(group, value, minimum):
        n, total, squared = stats[group]
        if n < minimum:
            return 0.0
        mean = total / n
        sd = math.sqrt(max(0, squared / n - mean * mean))
        return float(np.clip((value - mean) / (sd + .25), -10, 10))

    cursor = 0
    while cursor < len(ordered):
        end = cursor + 1
        ts = times[ordered[cursor]]
        while end < len(ordered) and times[ordered[end]] == ts:
            end += 1
        pending = []
        for i in ordered[cursor:end]:
            c, amount = claims[i], amounts[i]
            time_known = time_info[i][1]
            # Entity namespaces avoid mixing independent company histories.
            entity = key(c.get('entity_id'))
            v = (entity, key(c.get('vendor_id')) or key(c.get('vendor_name')))
            e = (entity, key(c.get('employee_id')))
            cat = (entity, key(c.get('category', c.get('general_ledger_account'))))
            pair = (e, v)
            groups = [('g', entity), ('v', v), ('e', e), ('c', cat), ('p', pair)]
            la = math.log1p(abs(amount))
            nv, ne, npair = (stats[g][0] for g in [groups[1], groups[2], groups[4]])
            for kind, group, days in [('v', v, 30), ('e', e, 7), ('p', pair, 1)]:
                queue = windows[(kind, group)]
                while queue and queue[0][0] <= ts - pd.Timedelta(days=days):
                    queue.popleft()
            pv, pe, pp = windows[('v', v)], windows[('e', e)], windows[('p', pair)]
            features = dict(log_amount=la, is_negative=float(amount < 0),
                is_round=float(abs(amount) >= 1000 and amount % 1000 == 0),
                hour=float(ts.hour), weekend_flag=float(ts.dayofweek >= 5),
                is_holiday=float(ts.date() in HOLIDAY_DATES),
                is_after_hours=float(time_known and (ts.hour < 8 or ts.hour >= 20)),
                z_global=zscore(groups[0], la, 50), z_vendor=zscore(groups[1], la, 3),
                z_employee=zscore(groups[2], la, 3), z_category=zscore(groups[3], la, 20),
                log_vendor_prior_n=math.log1p(min(nv, 30)), log_employee_prior_n=math.log1p(min(ne, 30)),
                vendor_is_new=float(nv == 0), employee_is_new=float(ne == 0), pair_is_new=float(npair == 0),
                vendor_missing=float(not v[1]), employee_missing=float(not e[1]),
                log_vendor_freq_30d=math.log1p(len(pv)), log_employee_freq_7d=math.log1p(len(pe)),
                log_days_since_vendor=math.log1p((ts - last_vendor[v]).total_seconds()/86400 if v in last_vendor else 365),
                duplicate_prior=float(any(abs(a - amount) < .005 for _, a in pp)),
                log_pair_amount_1d=math.log1p(sum(abs(a) for _, a in pp)), log_pair_count_1d=math.log1p(len(pp)))
            features.update(_ocr_features(c, amount))
            name = key(c.get('vendor_name'))
            features['vendor_name_deviation'] = 1 - max(
                (fuzz.ratio(name, key(known))/100 for known in config.KNOWN_VENDORS), default=0)
            output[i] = {name: float(features[name]) for name in FEATURE_NAMES}
            pending.append((groups, la, v, e, pair, amount))
        # Update only after every simultaneous transaction has been scored.
        for groups, la, v, e, pair, amount in pending:
            for group in groups:
                s = stats[group]
                s[0] += 1; s[1] += la; s[2] += la * la
            for kind, group in [('v', v), ('e', e), ('p', pair)]:
                windows[(kind, group)].append((ts, amount))
            last_vendor[v] = ts
        cursor = end
    return output, list(FEATURE_NAMES)


def compute_features(claim, all_claims, known_vendors=None):
    # Replace an existing row by ID to avoid inserting the target twice.
    cid = claim.get('claim_id', claim.get('transaction_id'))
    context = [c for c in all_claims if c is not claim and
               (cid is None or c.get('claim_id', c.get('transaction_id')) != cid)]
    return compute_features_batch(context + [claim])[0][-1]


def claim_record(c):
    """Shared DB adapter for training and scoring (including OCR quality)."""
    receipt = c.receipt
    ocr = receipt.ocr_result if receipt else None
    return dict(claim_id=c.claim_id, employee_id=c.employee_id, entity_id=c.entity_id,
                claimed_amount=float(c.claimed_amount), vendor_name=c.vendor_name,
                claimed_date=c.claimed_date, category=c.category,
                has_receipt=receipt is not None,
                ocr_amount=float(ocr.extracted_amount) if ocr and ocr.extracted_amount is not None else None,
                ocr_confidence=ocr.extraction_confidence if ocr else None,
                ocr_vendor=ocr.extracted_vendor if ocr else None,
                ocr_date=ocr.extracted_date if ocr else None)
