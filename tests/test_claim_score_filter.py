"""Score filtering and ordering operate on the full claim queue before pagination."""
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.auth.security import hash_password
from backend.app.db import Base, get_db
from backend.app.main import app
from backend.app.models.auth import AuthUser
from backend.app.models.expense import ExpenseClaim, FraudPrediction


def test_flagged_claims_can_be_filtered_and_sorted_by_displayed_score():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    def test_db():
        with session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = test_db
    try:
        with session_factory() as db:
            db.add(AuthUser(email="maker@auditai.example", employee_id="EMP014", display_name="Maker",
                            roles=["maker"], password_hash=hash_password("maker-pass-12345")))
            for claim_id, score, status in [
                ("LOW", .25, "flagged"),
                ("REVIEW", .55, "flagged"),
                ("HIGH-A", .81, "flagged"),
                ("HIGH-B", .93, "flagged"),
                ("UNSCORED", None, "flagged"),
                ("APPROVED", .99, "approved"),
            ]:
                db.add(ExpenseClaim(claim_id=claim_id, employee_id="EMP099", employee_name="Example",
                                    claimed_amount=Decimal("100.00"), vendor_name="Vendor",
                                    claimed_date=date(2026, 1, 15), status=status))
                if score is not None:
                    db.add(FraudPrediction(claim_id=claim_id, combined_fraud_score=score))
            db.commit()

        client = TestClient(app)
        login = client.post("/api/v1/auth/login", json={"email": "maker@auditai.example",
                                                   "password": "maker-pass-12345"})
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        def ids(**params):
            response = client.get("/api/v1/claims", headers=headers, params=params)
            assert response.status_code == 200, response.text
            return response.json()["total"], [claim["claim_id"] for claim in response.json()["claims"]]

        assert ids(status="flagged", score_band="high", sort_by="fraud_score", sort_order="desc") == (
            2, ["HIGH-B", "HIGH-A"])
        assert ids(status="flagged", score_band="high", sort_by="fraud_score", sort_order="asc") == (
            2, ["HIGH-A", "HIGH-B"])
        assert ids(status="flagged", score_band="review") == (1, ["REVIEW"])
        assert ids(status="flagged", score_band="low") == (1, ["LOW"])
        assert ids(status="flagged", sort_by="fraud_score", sort_order="desc", page_size=2, page=1) == (
            5, ["HIGH-B", "HIGH-A"])
        assert ids(status="flagged", sort_by="fraud_score", sort_order="desc", page_size=2, page=3) == (
            5, ["UNSCORED"])
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
