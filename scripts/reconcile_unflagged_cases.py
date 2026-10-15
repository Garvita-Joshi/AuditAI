"""Close system-only review cases whose claims are no longer flagged.

Keeps the case and its audit trail, adding a cancellation event. Human-reviewed
cases are never changed by this repair.
"""
from datetime import datetime
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.db import SessionLocal, engine
from backend.app.models.expense import Case
from backend.app.models.expense import CaseAuditTrail


def main():
    if engine.url.get_backend_name() != "sqlite":
        raise RuntimeError("This repair is for the local SQLite demo database only.")
    db_path = Path(engine.url.database).resolve()
    if db_path != (ROOT / "audit.db").resolve():
        raise RuntimeError("Unexpected database path; refusing to edit it.")

    with SessionLocal() as db:
        candidates = [
            case for case in db.query(Case).all()
            if case.status == "open"
            and not case.maker_id and not case.checker_id
            and case.claim.status == "scored"
            and case.claim.prediction and not case.claim.prediction.is_flagged
            and all(event.action == "created" and event.performed_by == "system"
                    for event in case.audit_trail)
        ]
        if not candidates:
            print("No stale system-only review cases found.")
            return

        backups = ROOT / "scripts" / "artifacts" / "case-reconciliation-backups"
        backups.mkdir(parents=True, exist_ok=True)
        backup = backups / f"audit-{datetime.now():%Y%m%d-%H%M%S}.sqlite3"
        with sqlite3.connect(db_path) as source, sqlite3.connect(backup) as destination:
            source.backup(destination)

        for case in candidates:
            case.status = "cancelled_unflagged"
            case.updated_at = datetime.utcnow()
            db.add(CaseAuditTrail(
                case_id=case.id,
                action="cancelled_after_rescore",
                performed_by="system",
                notes="The claim is no longer flagged; no reviewer had acted.",
            ))
        ids = [case.claim_id for case in candidates]
        db.commit()
        print(f"Cancelled {len(ids)} stale cases: {', '.join(ids)}. Backup: {backup}")


if __name__ == "__main__":
    main()
