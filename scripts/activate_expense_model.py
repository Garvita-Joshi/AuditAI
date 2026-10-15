"""Activate a validated expense model and restore supplied OCR metadata.

Only for the matching local synthetic expense CSV, never unrelated real claims.
Creates a SQLite backup and checks source identity before making any DB edits.
"""
from datetime import datetime
from pathlib import Path
import json
import shutil
import sqlite3
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from backend.app import config
from backend.app.db import SessionLocal, engine
from backend.app.models.expense import ExpenseClaim, Receipt, OcrResult
from backend.app.ml.pipeline import load_pipeline
from types import SimpleNamespace


def main():
    root = config.PROJECT_ROOT
    candidate = root / 'scripts/artifacts/expense-v2-candidate'
    bundle = load_pipeline(SimpleNamespace(TRAINED_MODELS_DIR=candidate))
    if bundle is None:
        raise ValueError('Train and verify the expense candidate first.')
    source = pd.read_csv(root / 'data/expense_claims.csv').set_index('claim_id')
    if not source.index.is_unique:
        raise ValueError('Source IDs must be unique.')
    if engine.url.get_backend_name() != 'sqlite':
        raise ValueError('This local synthetic migration requires SQLite.')
    db_path = Path(engine.url.database).resolve()
    if db_path != (root / 'audit.db').resolve():
        raise ValueError('Unexpected database; refusing migration.')
    session = SessionLocal()
    rows = session.query(ExpenseClaim).all()
    for c in rows:
        if c.claim_id not in source.index:
            raise ValueError('Database contains claims absent from the synthetic source.')
        r = source.loc[c.claim_id]
        if (abs(float(c.claimed_amount)-float(r.claimed_amount)) > .005 or
            c.vendor_name != r.vendor_name or c.employee_id != r.employee_id or
            str(c.claimed_date) != str(r.claimed_date) or bool(c.is_fraud) != bool(r.is_fraud)):
            raise ValueError(f'Source mismatch for {c.claim_id}; refusing migration.')
    backups = root / 'scripts/artifacts/model-backups'
    backups.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    with sqlite3.connect(db_path) as src, sqlite3.connect(backups / f'audit-{stamp}.sqlite3') as dst:
        src.backup(dst)
    old_model = config.TRAINED_MODELS_DIR / 'pipeline_v2.joblib'
    if old_model.exists():
        shutil.copy2(old_model, backups / f'pipeline-{stamp}.joblib')
    linked = 0
    for c in rows:
        value = source.loc[c.claim_id, 'ocr_amount']
        if c.receipt is None and pd.notna(value):
            receipt = Receipt(receipt_id=f'CSV-{uuid.uuid4().hex[:16]}', file_path='',
                              file_type='imported', upload_status='processed')
            receipt.ocr_result = OcrResult(extracted_amount=float(value), extraction_method='imported',
                                          extraction_confidence=None)
            c.receipt = receipt
            linked += 1
    session.commit()
    session.close()
    config.TRAINED_MODELS_DIR.mkdir(exist_ok=True, parents=True)
    temp = config.TRAINED_MODELS_DIR / 'pipeline_v2.pending'
    shutil.copy2(candidate / 'pipeline_v2.joblib', temp)
    temp.replace(old_model)
    shutil.copy2(candidate / 'training_report.json', config.TRAINED_MODELS_DIR / 'training_report.json')
    print(json.dumps({'matched_source_claims':len(rows), 'restored_imported_ocr_records':linked,
                      'selected_model':bundle['family'], 'backup_directory':str(backups)}))


if __name__ == '__main__':
    main()
