from sqlalchemy import Column, Integer, String, Numeric, Date, Time, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.db import Base

class Vendor(Base):
    __tablename__ = "vendors"

    vendor_name = Column(String, primary_key=True, index=True)
    gstin = Column(String, nullable=True)
    address = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    bank_account = Column(String, nullable=True)
    status = Column(String, nullable=False, default="Approved")  # Approved, Unapproved
    registration_date = Column(Date, nullable=True)

    # Relationship to transactions
    transactions = relationship("Transaction", back_populates="vendor")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    txn_id = Column(String, unique=True, index=True, nullable=False)
    date = Column(Date, index=True, nullable=False)
    time = Column(Time, nullable=True)
    vendor_name = Column(String, ForeignKey("vendors.vendor_name"), nullable=False)
    amount = Column(Numeric(precision=15, scale=2), nullable=False)
    payment_method = Column(String, nullable=True)
    created_by = Column(String, nullable=True)
    approved_by = Column(String, nullable=True)
    account_head = Column(String, nullable=True)
    is_fraud = Column(Boolean, default=False, nullable=False)
    fraud_type = Column(String, default="none", nullable=False)

    # Relationship to vendor
    vendor = relationship("Vendor", back_populates="transactions")
