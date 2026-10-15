"""Create local demo accounts and write one-time passwords to an ignored file."""
import os
from pathlib import Path
import secrets
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.auth.security import normalize_company_email
from backend.app.db import Base, SessionLocal, engine
from backend.app.models.auth import AuthUser
from backend.app.models import expense  # noqa: F401
from scripts.provision_user import provision

CREDENTIALS_FILE = ROOT / "scripts" / "artifacts" / "demo-credentials.txt"
DEMO_ACCOUNTS = [
    ("employee@auditai.example", "EMP001", "Demo Employee", ["employee"]),
    ("maker@auditai.example", "EMP014", "Demo Maker", ["employee", "maker"]),
    ("checker@auditai.example", "EMP033", "Demo Checker", ["employee", "checker"]),
    ("dual@auditai.example", "EMP050", "Demo Dual Reviewer", ["employee", "maker", "checker"]),
    ("admin@auditai.example", "EMP-ADMIN", "Demo Administrator", ["admin"]),
]


def main():
    for email, *_ in DEMO_ACCOUNTS:
        normalize_company_email(email)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        already_exist = [email for email, *_ in DEMO_ACCOUNTS
                         if db.query(AuthUser).filter(AuthUser.email == email).first()]
    if already_exist and not CREDENTIALS_FILE.exists():
        raise RuntimeError("Demo accounts exist but their one-time password file is missing. Reset them with provision_user.py.")
    lines = (CREDENTIALS_FILE.read_text(encoding="utf-8").splitlines() if CREDENTIALS_FILE.exists()
             else ["AuditAI local demo accounts", "These passwords are for local testing. Change them before real use.", ""])
    created = 0
    for email, employee_id, name, roles in DEMO_ACCOUNTS:
        if email in already_exist:
            continue
        password = secrets.token_urlsafe(18)
        provision(email, employee_id, name, roles, password)
        lines.append(f"{email} | {password} | {employee_id} | {','.join(roles)}")
        created += 1
    CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    CREDENTIALS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if os.name != "nt":
        CREDENTIALS_FILE.chmod(0o600)
    print(f"Created {created} demo accounts. Credentials: {CREDENTIALS_FILE}")


if __name__ == "__main__":
    main()
