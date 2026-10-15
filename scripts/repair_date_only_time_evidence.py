"""Repair fabricated midnight evidence in the local synthetic expense database.

The import has claim dates but no transaction time. Verify that the corrected
feature vectors produce exactly the same saved model scores before changing
persisted evidence. Keep case decisions and generated reports untouched.
"""
from collections import Counter
from datetime import datetime
from pathlib import Path
import sqlite3
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app import config
from backend.app.db import SessionLocal, engine
from backend.app.features.behavioral import FEATURE_NAMES, claim_record, compute_features_batch
from backend.app.ml.pipeline import load_pipeline, score_claims
from backend.app.models.expense import ExpenseClaim


def main():
    if engine.url.get_backend_name() != "sqlite":
        raise RuntimeError("This repair is only for the local SQLite demo database.")
    db_path = Path(engine.url.database).resolve()
    if db_path != (ROOT / "audit.db").resolve():
        raise RuntimeError("Unexpected database path; refusing to edit it.")
    pipeline = load_pipeline(config)
    if pipeline is None:
        raise RuntimeError("No active model bundle found.")

    with SessionLocal() as db:
        claims = db.query(ExpenseClaim).order_by(ExpenseClaim.submitted_at, ExpenseClaim.id).all()
        features, names = compute_features_batch([claim_record(claim) for claim in claims])
        if set(names) != set(FEATURE_NAMES):
            raise RuntimeError("Feature schema changed; refusing automatic repair.")
        matrix = np.asarray([[row[name] for name in names] for row in features])
        scores = score_claims(matrix, pipeline, config)
        changes = Counter()
        for claim, row, score in zip(claims, features, scores):
            prediction = claim.prediction
            if prediction is None or prediction.feature_values is None:
                raise RuntimeError(f"Missing stored prediction for {claim.claim_id}.")
            if abs(prediction.combined_fraud_score - score["combined_fraud_score"]) > 1e-9:
                raise RuntimeError(f"Score changed for {claim.claim_id}; repair requires a full rescore.")
            differences = {name for name in names
                           if abs(float(prediction.feature_values.get(name, 0)) - row[name]) > 1e-9}
            if differences - {"hour", "is_after_hours"}:
                raise RuntimeError(f"Other features changed for {claim.claim_id}: {differences}")
            changes.update(differences)

        backups = ROOT / "scripts" / "artifacts" / "time-evidence-backups"
        backups.mkdir(parents=True, exist_ok=True)
        backup = backups / f"audit-{datetime.now():%Y%m%d-%H%M%S}.sqlite3"
        with sqlite3.connect(db_path) as source, sqlite3.connect(backup) as destination:
            source.backup(destination)

        for claim, row in zip(claims, features):
            prediction = claim.prediction
            prediction.feature_values = {
                **prediction.feature_values,
                "hour": row["hour"],
                "is_after_hours": row["is_after_hours"],
                "_event_time_known": 0.0,
            }
        db.commit()
    print(f"Corrected {len(claims)} date-only predictions; changed {dict(changes)}. Backup: {backup}")


if __name__ == "__main__":
    main()
