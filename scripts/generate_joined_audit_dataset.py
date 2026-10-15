import os
import random
import datetime
import math
import numpy as np
import pandas as pd
from faker import Faker

# Set random seeds for reproducibility
random.seed(42)
np.random.seed(42)
fake = Faker('en_IN')

# Define target directories
DATA_DIR = "./data"
AUDIT_DATA_DIR = "./auditData"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(AUDIT_DATA_DIR, exist_ok=True)

print("Starting generation of AuditAI Master Joined Anomaly & Safe Dataset...")

# ----------------------------------------------------
# 1. Master Reference Entities
# ----------------------------------------------------

DEPARTMENTS = [
    {"department_id": "DEP001", "department_name": "Finance"},
    {"department_id": "DEP002", "department_name": "HR"},
    {"department_id": "DEP003", "department_name": "IT"},
    {"department_id": "DEP004", "department_name": "Procurement"},
    {"department_id": "DEP005", "department_name": "Operations"},
    {"department_id": "DEP006", "department_name": "Sales"},
    {"department_id": "DEP007", "department_name": "Marketing"}
]

EMPLOYEES = [
    {"employee_id": "EMP001", "employee_name": "Rajesh Subramanian", "designation": "CEO", "department_id": "DEP005", "approval_limit": 100000000},
    {"employee_id": "EMP002", "employee_name": "Vikram Malhotra", "designation": "CFO", "department_id": "DEP001", "approval_limit": 50000000},
    {"employee_id": "EMP003", "employee_name": "Priya Patel", "designation": "VP", "department_id": "DEP001", "approval_limit": 5000000},
    {"employee_id": "EMP004", "employee_name": "Amit Sharma", "designation": "VP", "department_id": "DEP003", "approval_limit": 5000000},
    {"employee_id": "EMP005", "employee_name": "Sanjay Verma", "designation": "Director", "department_id": "DEP004", "approval_limit": 1000000},
    {"employee_id": "EMP006", "employee_name": "Neha Gupta", "designation": "Director", "department_id": "DEP006", "approval_limit": 1000000},
    {"employee_id": "EMP007", "employee_name": "Rahul Sharma", "designation": "Senior Manager", "department_id": "DEP004", "approval_limit": 250000},
    {"employee_id": "EMP008", "employee_name": "Anil Mehta", "designation": "Senior Manager", "department_id": "DEP001", "approval_limit": 250000},
    {"employee_id": "EMP009", "employee_name": "Sneha Reddy", "designation": "Manager", "department_id": "DEP004", "approval_limit": 50000},
    {"employee_id": "EMP010", "employee_name": "Kiran Rao", "designation": "Manager", "department_id": "DEP006", "approval_limit": 50000},
    {"employee_id": "EMP011", "employee_name": "Pooja Joshi", "designation": "Associate", "department_id": "DEP004", "approval_limit": 0},
    {"employee_id": "EMP012", "employee_name": "Rohan Deshmukh", "designation": "Associate", "department_id": "DEP006", "approval_limit": 0},
    {"employee_id": "EMP013", "employee_name": "Deepak Kumar", "designation": "Associate", "department_id": "DEP003", "approval_limit": 0},
    {"employee_id": "EMP014", "employee_name": "Ananya Nair", "designation": "Associate", "department_id": "DEP002", "approval_limit": 0},
    {"employee_id": "EMP015", "employee_name": "Siddharth Menon", "designation": "Associate", "department_id": "DEP007", "approval_limit": 0}
]

VENDORS = [
    {"vendor_id": "VEN001", "vendor_name": "Reliance Industries Ltd", "category": "Raw Materials", "gstin": "27AAACR0123A1Z5", "status": "Verified"},
    {"vendor_id": "VEN002", "vendor_name": "Tata Consultancy Services Ltd", "category": "Consulting & Professional Services", "gstin": "27AAACT1234B1Z6", "status": "Verified"},
    {"vendor_id": "VEN003", "vendor_name": "Infosys Technologies Ltd", "category": "IT Hardware & Software", "gstin": "29AAACI5678C1Z7", "status": "Verified"},
    {"vendor_id": "VEN004", "vendor_name": "Bharti Airtel Ltd", "category": "Facilities & Utilities", "gstin": "07AAACB9012D1Z8", "status": "Verified"},
    {"vendor_id": "VEN005", "vendor_name": "Larsen & Toubro Ltd", "category": "Raw Materials", "gstin": "27AAACL3456E1Z9", "status": "Verified"},
    {"vendor_id": "VEN006", "vendor_name": "Blue Dart Express Ltd", "category": "Logistics & Courier", "gstin": "27AAACB7890F1Z0", "status": "Verified"},
    {"vendor_id": "VEN007", "vendor_name": "Apex Travel Solutions", "category": "Travel & Lodging", "gstin": "07AAACA1234G1Z1", "status": "Verified"},
    {"vendor_id": "VEN008", "vendor_name": "J2 Office Supplies Pvt Ltd", "category": "Office Supplies", "gstin": "27AAACJ5678H1Z2", "status": "Verified"},
    {"vendor_id": "VEN009", "vendor_name": "Modern Stationers", "category": "Office Supplies", "gstin": "27AAACM9012I1Z3", "status": "Verified"},
    {"vendor_id": "VEN010", "vendor_name": "FastTrack Logistics", "category": "Logistics & Courier", "gstin": "33AAACF3456J1Z4", "status": "Verified"},

    # Anomalous / Suspicious vendors
    {"vendor_id": "VEN901", "vendor_name": "Krishna Trading Co", "category": "Raw Materials", "gstin": "07AAACK6188A1Z5", "status": "Shell Network"},
    {"vendor_id": "VEN902", "vendor_name": "K Trading Solutions", "category": "Raw Materials", "gstin": "07AAACK6188A2Z6", "status": "Shell Network"},
    {"vendor_id": "VEN903", "vendor_name": "Sharma Tea & Catering Services", "category": "Office Supplies", "gstin": "99INVALID0000Z0", "status": "Unverified Fake"},
    {"vendor_id": "VEN904", "vendor_name": "Infosys Technologys Pvt Ltd", "category": "IT Hardware & Software", "gstin": "29AAACI9999X1Z9", "status": "Typosquatted Fake"},
    {"vendor_id": "VEN905", "vendor_name": "Global Offshore Holdings BVI", "category": "Consulting & Professional Services", "gstin": "FOREIGN-BVI-99", "status": "Offshore Shell"},
    {"vendor_id": "VEN906", "vendor_name": "Verma Consulting Services", "category": "Consulting & Professional Services", "gstin": "07AAACV4321K1Z2", "status": "Related Party"}
]

ACCOUNT_HEADS = [
    "Office Supplies", "Travel & Entertainment", "Consulting & Professional Fees", "Marketing & Advertising",
    "IT Hardware & Software", "Facilities & Utilities", "Salaries & Payroll", "Rent & Leases", "Logistics & Freight",
    "Raw Materials Procurement", "Financial Instruments & Derivatives", "Revenue & Sales", "Miscellaneous & Adjustments"
]

START_DATE = datetime.date(2025, 4, 1)
END_DATE = datetime.date(2026, 3, 31)
TOTAL_DAYS = (END_DATE - START_DATE).days

def random_date_in_range(start=START_DATE, end=END_DATE):
    delta_days = (end - start).days
    return start + datetime.timedelta(days=random.randint(0, delta_days))

def random_time_business():
    hour = random.randint(9, 18)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return f"{hour:02d}:{minute:02d}:{second:02d}"

def random_time_after_hours():
    hour = random.choice([23, 0, 1, 2, 3, 4])
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return f"{hour:02d}:{minute:02d}:{second:02d}"


# ----------------------------------------------------
# 2. GENERATE ALL 25 ANOMALY TYPES + SAFE TRANSACTIONS
# ----------------------------------------------------

records = []
txn_id_counter = 1

# List of all 25 Anomaly Categories specified by the user prompt
ANOMALY_CATEGORIES = [
    "Duplicate payment / duplicate entry",
    "Split invoice / threshold dodging",
    "Manual journal-entry manipulation",
    "Revenue manipulation / cut-off risk",
    "Vendor or invoice fraud",
    "Ghost vendor risk",
    "Related-party risk",
    "Expense and corporate-card fraud",
    "Payroll fraud risk",
    "Cash-payment risk",
    "Suspicious wording",
    "Round-number or last-digit manipulation",
    "Unusual amount",
    "High monetary value",
    "Rare flow",
    "Unusual flow",
    "Sequence gaps",
    "Reversal risk",
    "Missing information / unintentional errors",
    "Weekend and after-hours posting",
    "Complex structure risk",
    "Complex financial-instrument risk",
    "Benford's Law anomalies",
    "ML-based unknown or emerging risk",
    "Expense receipt mismatch"
]

print("Generating 8,000 Safe (Normal) Transactions...")
# Generate 8,000 safe normal transactions
for _ in range(8000):
    t_id = f"TXN{txn_id_counter:06d}"
    t_date = random_date_in_range()
    t_time = random_time_business()
    emp = random.choice(EMPLOYEES)
    dept = next(d for d in DEPARTMENTS if d['department_id'] == emp['department_id'])
    v = random.choice(VENDORS[:10]) # Normal verified vendors
    head = random.choice(ACCOUNT_HEADS[:10])
    
    # Normal realistic lognormal amount
    amt = round(float(np.random.lognormal(mean=9.2, sigma=0.9)), 2)
    amt = max(1200.0, min(amt, 350000.0))
    # Not round number
    if amt.is_integer():
        amt += 0.45
        
    pmode = random.choice(["NEFT", "RTGS", "Bank Transfer", "Credit Card"])
    inv_id = f"INV-{t_date.year}-{random.randint(10000, 99999)}"
    
    # Valid approver
    valid_apps = [e for e in EMPLOYEES if e['approval_limit'] >= amt and e['employee_id'] != emp['employee_id']]
    app = random.choice(valid_apps) if valid_apps else EMPLOYEES[0]
    
    ocr_amt = amt
    claim_amt = amt
    
    records.append({
        "transaction_id": t_id,
        "transaction_date": str(t_date),
        "transaction_time": t_time,
        "entry_type": "Automated ERP Entry",
        "general_ledger_account": head,
        "amount": amt,
        "currency": "INR",
        "vendor_id": v['vendor_id'],
        "vendor_name": v['vendor_name'],
        "invoice_id": inv_id,
        "employee_id": emp['employee_id'],
        "employee_name": emp['employee_name'],
        "department_id": dept['department_id'],
        "department_name": dept['department_name'],
        "approved_by_id": app['employee_id'],
        "approved_by_name": app['employee_name'],
        "payment_mode": pmode,
        "description": f"Standard recurring payment for {head.lower()} to {v['vendor_name']}",
        "ocr_extracted_amount": ocr_amt,
        "receipt_claimed_amount": claim_amt,
        "is_anomaly": 0,
        "risk_category": "Safe Transaction",
        "risk_severity": "Safe",
        "risk_score": round(random.uniform(0.01, 0.12), 4),
        "detected_risk_signals": "NONE",
        "audit_explanation": "Normal business transaction with verified vendor, valid approval authority, and routine operational pattern."
    })
    txn_id_counter += 1


print("Injecting 2,000 Anomaly / Risk Signal Transactions (80 records per category x 25 categories)...")

# 1. Duplicate payment / duplicate entry (80 txns = 40 pairs)
for _ in range(40):
    v = random.choice(VENDORS[:10])
    amt = round(float(random.randint(25000, 450000)) + 0.50, 2)
    t_date = random_date_in_range()
    inv = f"INV-DUP-{t_date.year}-{random.randint(1000, 9999)}"
    emp = random.choice(EMPLOYEES[6:10])
    dept = next(d for d in DEPARTMENTS if d['department_id'] == emp['department_id'])
    
    for dup_i in range(2):
        t_id = f"TXN{txn_id_counter:06d}"
        d_date = t_date + datetime.timedelta(days=dup_i)
        inv_str = inv if dup_i == 0 else f"{inv}-A"
        
        records.append({
            "transaction_id": t_id,
            "transaction_date": str(d_date),
            "transaction_time": random_time_business(),
            "entry_type": "Automated ERP Entry",
            "general_ledger_account": "Consulting & Professional Fees",
            "amount": amt,
            "currency": "INR",
            "vendor_id": v['vendor_id'],
            "vendor_name": v['vendor_name'],
            "invoice_id": inv_str,
            "employee_id": emp['employee_id'],
            "employee_name": emp['employee_name'],
            "department_id": dept['department_id'],
            "department_name": dept['department_name'],
            "approved_by_id": "EMP003",
            "approved_by_name": "Priya Patel",
            "payment_mode": "NEFT",
            "description": f"Payment for quarterly advisory services invoice {inv_str}",
            "ocr_extracted_amount": amt,
            "receipt_claimed_amount": amt,
            "is_anomaly": 1,
            "risk_category": "Duplicate payment / duplicate entry",
            "risk_severity": "High",
            "risk_score": 0.88,
            "detected_risk_signals": "DUPLICATE_PAYMENT|SAME_VENDOR_AMOUNT_WINDOW",
            "audit_explanation": f"Duplicate payment indicator: Identical amount ₹{amt:,.2f} paid to vendor {v['vendor_name']} within 24 hours."
        })
        txn_id_counter += 1

# 2. Split invoice / threshold dodging (80 txns = 20 groups of 4)
for _ in range(20):
    v = random.choice(VENDORS[:10])
    s_date = random_date_in_range()
    mgr = EMPLOYEES[8] # Limit 50,000
    subordinate = EMPLOYEES[10] # Associate
    dept = next(d for d in DEPARTMENTS if d['department_id'] == subordinate['department_id'])
    
    for i in range(4):
        t_id = f"TXN{txn_id_counter:06d}"
        amt = round(float(random.randint(47000, 49800) + random.random()), 2)
        records.append({
            "transaction_id": t_id,
            "transaction_date": str(s_date + datetime.timedelta(days=i%2)),
            "transaction_time": random_time_business(),
            "entry_type": "Automated ERP Entry",
            "general_ledger_account": "Raw Materials Procurement",
            "amount": amt,
            "currency": "INR",
            "vendor_id": v['vendor_id'],
            "vendor_name": v['vendor_name'],
            "invoice_id": f"INV-SPL-{random.randint(10000, 99999)}",
            "employee_id": subordinate['employee_id'],
            "employee_name": subordinate['employee_name'],
            "department_id": dept['department_id'],
            "department_name": dept['department_name'],
            "approved_by_id": mgr['employee_id'],
            "approved_by_name": mgr['employee_name'],
            "payment_mode": "NEFT",
            "description": f"Partial batch supply procurement invoice split part {i+1}",
            "ocr_extracted_amount": amt,
            "receipt_claimed_amount": amt,
            "is_anomaly": 1,
            "risk_category": "Split invoice / threshold dodging",
            "risk_severity": "High",
            "risk_score": 0.85,
            "detected_risk_signals": "SPLIT_INVOICE|THRESHOLD_DODGING",
            "audit_explanation": f"Threshold dodging: Multiple smaller payments (~₹{amt:,.2f}) structured below Manager's ₹50,000 approval limit, totaling ₹1,90,000+."
        })
        txn_id_counter += 1

# 3. Manual journal-entry manipulation (80 txns)
for _ in range(80):
    t_id = f"TXN{txn_id_counter:06d}"
    t_date = random_date_in_range()
    emp = EMPLOYEES[7] # Senior Manager Finance
    dept = DEPARTMENTS[0] # Finance
    amt = round(float(random.randint(500000, 2500000)), 2)
    
    records.append({
        "transaction_id": t_id,
        "transaction_date": str(t_date),
        "transaction_time": random_time_business(),
        "entry_type": "Manual Journal Entry",
        "general_ledger_account": "Miscellaneous & Adjustments",
        "amount": amt,
        "currency": "INR",
        "vendor_id": "",
        "vendor_name": "Direct Journal Posting",
        "invoice_id": f"JV-{t_date.year}-{random.randint(1000, 9999)}",
        "employee_id": emp['employee_id'],
        "employee_name": emp['employee_name'],
        "department_id": dept['department_id'],
        "department_name": dept['department_name'],
        "approved_by_id": "EMP002",
        "approved_by_name": "Vikram Malhotra",
        "payment_mode": "Manual Journal Entry",
        "description": "Manual debit adjustment for unvouched end-of-period provision rounding balance",
        "ocr_extracted_amount": 0.0,
        "receipt_claimed_amount": 0.0,
        "is_anomaly": 1,
        "risk_category": "Manual journal-entry manipulation",
        "risk_severity": "Critical",
        "risk_score": 0.92,
        "detected_risk_signals": "MANUAL_JOURNAL_ENTRY|HIGH_VALUE_UNVOUCHED_ADJUSTMENT",
        "audit_explanation": f"Manual journal entry manipulation: High-value manual journal entry of ₹{amt:,.2f} posted directly without supporting invoice or vendor voucher."
    })
    txn_id_counter += 1

# 4. Revenue manipulation / cut-off risk (80 txns)
cut_off_dates = [datetime.date(2025, 6, 30), datetime.date(2025, 9, 30), datetime.date(2025, 12, 31), datetime.date(2026, 3, 31)]
for _ in range(80):
    t_id = f"TXN{txn_id_counter:06d}"
    t_date = random.choice(cut_off_dates)
    emp = EMPLOYEES[5] # Director Sales
    dept = DEPARTMENTS[5] # Sales
    amt = round(float(random.randint(1500000, 6000000)), 2)
    
    records.append({
        "transaction_id": t_id,
        "transaction_date": str(t_date),
        "transaction_time": "23:45:10",
        "entry_type": "Manual Journal Entry",
        "general_ledger_account": "Revenue & Sales",
        "amount": amt,
        "currency": "INR",
        "vendor_id": "",
        "vendor_name": "Unverified Client Booking",
        "invoice_id": f"REV-{t_date.year}-{random.randint(1000, 9999)}",
        "employee_id": emp['employee_id'],
        "employee_name": emp['employee_name'],
        "department_id": dept['department_id'],
        "department_name": dept['department_name'],
        "approved_by_id": "EMP001",
        "approved_by_name": "Rajesh Subramanian",
        "payment_mode": "Manual Journal Entry",
        "description": "Quarterly cutoff revenue recognition posting for pending contract execution",
        "ocr_extracted_amount": 0.0,
        "receipt_claimed_amount": 0.0,
        "is_anomaly": 1,
        "risk_category": "Revenue manipulation / cut-off risk",
        "risk_severity": "High",
        "risk_score": 0.89,
        "detected_risk_signals": "REVENUE_CUTOFF_RISK|PERIOD_END_POSTING",
        "audit_explanation": f"Revenue cut-off risk: Massive revenue posting of ₹{amt:,.2f} recorded on the exact final day of the financial reporting period."
    })
    txn_id_counter += 1

# 5. Vendor or invoice fraud (80 txns)
fake_vendors = [VENDORS[12], VENDORS[13]] # Sharma Tea with 99 GSTIN & Typosquatted Infosys
for _ in range(80):
    t_id = f"TXN{txn_id_counter:06d}"
    t_date = random_date_in_range()
    v = random.choice(fake_vendors)
    emp = EMPLOYEES[10]
    dept = DEPARTMENTS[3]
    amt = round(float(random.randint(45000, 320000)), 2)
    
    records.append({
        "transaction_id": t_id,
        "transaction_date": str(t_date),
        "transaction_time": random_time_business(),
        "entry_type": "Automated ERP Entry",
        "general_ledger_account": "IT Hardware & Software",
        "amount": amt,
        "currency": "INR",
        "vendor_id": v['vendor_id'],
        "vendor_name": v['vendor_name'],
        "invoice_id": f"INV-FAKE-{random.randint(1000, 9999)}",
        "employee_id": emp['employee_id'],
        "employee_name": emp['employee_name'],
        "department_id": dept['department_id'],
        "department_name": dept['department_name'],
        "approved_by_id": "EMP007",
        "approved_by_name": "Rahul Sharma",
        "payment_mode": "NEFT",
        "description": f"Software license renewal fee paid to {v['vendor_name']}",
        "ocr_extracted_amount": amt,
        "receipt_claimed_amount": amt,
        "is_anomaly": 1,
        "risk_category": "Vendor or invoice fraud",
        "risk_severity": "Critical",
        "risk_score": 0.95,
        "detected_risk_signals": "INVALID_GSTIN|TYPOSQUATTED_VENDOR|FAKE_VENDOR_INVOICE",
        "audit_explanation": f"Vendor fraud detected: Invoice paid to unverified/fake vendor {v['vendor_name']} with invalid GSTIN ({v['gstin']})."
    })
    txn_id_counter += 1

# 6. Ghost vendor risk (80 txns)
for _ in range(80):
    t_id = f"TXN{txn_id_counter:06d}"
    t_date = random_date_in_range()
    emp = EMPLOYEES[6]
    dept = DEPARTMENTS[3]
    amt = round(float(random.randint(800000, 2800000)), 2)
    g_name = f"Apex Ghost Enterprise {random.randint(100, 999)}"
    
    records.append({
        "transaction_id": t_id,
        "transaction_date": str(t_date),
        "transaction_time": random_time_business(),
        "entry_type": "Automated ERP Entry",
        "general_ledger_account": "Consulting & Professional Fees",
        "amount": amt,
        "currency": "INR",
        "vendor_id": f"VEN-GHOST-{random.randint(100, 999)}",
        "vendor_name": g_name,
        "invoice_id": f"INV-GHOST-{random.randint(1000, 9999)}",
        "employee_id": emp['employee_id'],
        "employee_name": emp['employee_name'],
        "department_id": dept['department_id'],
        "department_name": dept['department_name'],
        "approved_by_id": "EMP003",
        "approved_by_name": "Priya Patel",
        "payment_mode": "RTGS",
        "description": f"First-time retainer payment for strategic digital transformation consulting",
        "ocr_extracted_amount": amt,
        "receipt_claimed_amount": amt,
        "is_anomaly": 1,
        "risk_category": "Ghost vendor risk",
        "risk_severity": "High",
        "risk_score": 0.87,
        "detected_risk_signals": "GHOST_VENDOR|ZERO_HISTORICAL_TXN|FIRST_TIME_HIGH_VALUE",
        "audit_explanation": f"Ghost vendor risk: Large disbursement of ₹{amt:,.2f} issued to first-time vendor {g_name} with zero prior ledger history."
    })
    txn_id_counter += 1

# 7. Related-party risk (80 txns)
v_related = VENDORS[15] # Verma Consulting Services linked to Sanjay Verma / Rajesh Verma
for _ in range(80):
    t_id = f"TXN{txn_id_counter:06d}"
    t_date = random_date_in_range()
    emp = EMPLOYEES[4] # Sanjay Verma
    dept = DEPARTMENTS[3]
    amt = round(float(random.randint(150000, 750000)), 2)
    
    records.append({
        "transaction_id": t_id,
        "transaction_date": str(t_date),
        "transaction_time": random_time_business(),
        "entry_type": "Automated ERP Entry",
        "general_ledger_account": "Consulting & Professional Fees",
        "amount": amt,
        "currency": "INR",
        "vendor_id": v_related['vendor_id'],
        "vendor_name": v_related['vendor_name'],
        "invoice_id": f"INV-REL-{random.randint(1000, 9999)}",
        "employee_id": emp['employee_id'],
        "employee_name": emp['employee_name'],
        "department_id": dept['department_id'],
        "department_name": dept['department_name'],
        "approved_by_id": "EMP002",
        "approved_by_name": "Vikram Malhotra",
        "payment_mode": "NEFT",
        "description": "Specialized procurement audit consultancy fee paid to Verma Consulting Services",
        "ocr_extracted_amount": amt,
        "receipt_claimed_amount": amt,
        "is_anomaly": 1,
        "risk_category": "Related-party risk",
        "risk_severity": "High",
        "risk_score": 0.86,
        "detected_risk_signals": "RELATED_PARTY_CONFLICT|SURNAME_ADDRESS_OVERLAP",
        "audit_explanation": f"Related-party risk: Vendor {v_related['vendor_name']} shares entity ownership surname / conflict of interest with employee {emp['employee_name']}."
    })
    txn_id_counter += 1

# 8. Expense and corporate-card fraud (80 txns)
personal_descriptions = [
    "Family weekend dinner at Taj Hotel",
    "Grocery shopping at D-Mart Supermarket",
    "Personal holiday resort package booking",
    "Luxury wristwatch purchase for personal gift",
    "Electronics purchase - iPhone 16 Pro Max for family member"
]
for _ in range(80):
    t_id = f"TXN{txn_id_counter:06d}"
    t_date = random_date_in_range()
    desc = random.choice(personal_descriptions)
    emp = random.choice(EMPLOYEES[9:15])
    dept = next(d for d in DEPARTMENTS if d['department_id'] == emp['department_id'])
    amt = round(float(random.randint(12000, 85000)), 2)
    
    records.append({
        "transaction_id": t_id,
        "transaction_date": str(t_date),
        "transaction_time": random_time_business(),
        "entry_type": "Expense Claim",
        "general_ledger_account": "Travel & Entertainment",
        "amount": amt,
        "currency": "INR",
        "vendor_id": "",
        "vendor_name": "Retail Store / Hotel Merchant",
        "invoice_id": f"EXP-{random.randint(10000, 99999)}",
        "employee_id": emp['employee_id'],
        "employee_name": emp['employee_name'],
        "department_id": dept['department_id'],
        "department_name": dept['department_name'],
        "approved_by_id": "EMP009",
        "approved_by_name": "Sneha Reddy",
        "payment_mode": "Credit Card",
        "description": desc,
        "ocr_extracted_amount": amt,
        "receipt_claimed_amount": amt,
        "is_anomaly": 1,
        "risk_category": "Expense and corporate-card fraud",
        "risk_severity": "Medium",
        "risk_score": 0.78,
        "detected_risk_signals": "PERSONAL_EXPENSE_FRAUD|NON_BUSINESS_MERCHANT",
        "audit_explanation": f"Corporate card fraud: Personal expense '{desc}' submitted under corporate business travel expense claims."
    })
    txn_id_counter += 1

# 9. Payroll fraud risk (80 txns)
for _ in range(80):
    t_id = f"TXN{txn_id_counter:06d}"
    t_date = random_date_in_range()
    amt = round(float(random.randint(350000, 1200000)), 2)
    ghost_emp_id = f"EMP-GHOST-{random.randint(900, 999)}"
    
    records.append({
        "transaction_id": t_id,
        "transaction_date": str(t_date),
        "transaction_time": random_time_business(),
        "entry_type": "Manual Journal Entry",
        "general_ledger_account": "Salaries & Payroll",
        "amount": amt,
        "currency": "INR",
        "vendor_id": "",
        "vendor_name": f"Off-Cycle Payroll - {ghost_emp_id}",
        "invoice_id": f"SLY-MAN-{random.randint(1000, 9999)}",
        "employee_id": ghost_emp_id,
        "employee_name": "Unregistered Staff Member",
        "department_id": "DEP002",
        "department_name": "HR",
        "approved_by_id": "EMP008",
        "approved_by_name": "Anil Mehta",
        "payment_mode": "Manual Journal Entry",
        "description": "Manual off-cycle payroll bonus disbursement to inactive employee master record",
        "ocr_extracted_amount": 0.0,
        "receipt_claimed_amount": 0.0,
        "is_anomaly": 1,
        "risk_category": "Payroll fraud risk",
        "risk_severity": "Critical",
        "risk_score": 0.94,
        "detected_risk_signals": "GHOST_EMPLOYEE_PAYROLL|MANUAL_PAYROLL_ADJUSTMENT",
        "audit_explanation": f"Payroll fraud risk: Manual payroll entry of ₹{amt:,.2f} directed to unverified employee ID {ghost_emp_id} outside standard payroll batch runs."
    })
    txn_id_counter += 1

# 10. Cash-payment risk (80 txns)
for _ in range(80):
    t_id = f"TXN{txn_id_counter:06d}"
    t_date = random_date_in_range()
    emp = random.choice(EMPLOYEES[6:10])
    dept = next(d for d in DEPARTMENTS if d['department_id'] == emp['department_id'])
    amt = round(float(random.randint(75000, 450000)), 2)
    
    records.append({
        "transaction_id": t_id,
        "transaction_date": str(t_date),
        "transaction_time": random_time_business(),
        "entry_type": "Automated ERP Entry",
        "general_ledger_account": "Miscellaneous & Adjustments",
        "amount": amt,
        "currency": "INR",
        "vendor_id": "",
        "vendor_name": "Cash Petty Disbursement",
        "invoice_id": f"CSH-{random.randint(1000, 9999)}",
        "employee_id": emp['employee_id'],
        "employee_name": emp['employee_name'],
        "department_id": dept['department_id'],
        "department_name": dept['department_name'],
        "approved_by_id": "EMP003",
        "approved_by_name": "Priya Patel",
        "payment_mode": "Cash",
        "description": "Urgent cash payment for unvouched vendor service settlement",
        "ocr_extracted_amount": 0.0,
        "receipt_claimed_amount": 0.0,
        "is_anomaly": 1,
        "risk_category": "Cash-payment risk",
        "risk_severity": "High",
        "risk_score": 0.84,
        "detected_risk_signals": "HIGH_VALUE_CASH|WEAK_AUDIT_TRAIL",
        "audit_explanation": f"Cash payment risk: High-value cash payout of ₹{amt:,.2f} violating corporate electronic banking mandates."
    })
    txn_id_counter += 1

# 11. Suspicious wording (80 txns)
words = ["adjustment", "misc", "personal", "reimburse", "cash", "urgent", "one-time", "off-the-books"]
for _ in range(80):
    t_id = f"TXN{txn_id_counter:06d}"
    t_date = random_date_in_range()
    word = random.choice(words)
    amt = round(float(random.randint(60000, 350000)), 2)
    emp = EMPLOYEES[7]
    dept = DEPARTMENTS[0]
    
    records.append({
        "transaction_id": t_id,
        "transaction_date": str(t_date),
        "transaction_time": random_time_business(),
        "entry_type": "Manual Journal Entry",
        "general_ledger_account": "Miscellaneous & Adjustments",
        "amount": amt,
        "currency": "INR",
        "vendor_id": "",
        "vendor_name": "Sundry Vendor",
        "invoice_id": f"INV-SUS-{random.randint(1000, 9999)}",
        "employee_id": emp['employee_id'],
        "employee_name": emp['employee_name'],
        "department_id": dept['department_id'],
        "department_name": dept['department_name'],
        "approved_by_id": "EMP002",
        "approved_by_name": "Vikram Malhotra",
        "payment_mode": "NEFT",
        "description": f"Special confidential {word} payout for executive discretionary settlement",
        "ocr_extracted_amount": amt,
        "receipt_claimed_amount": amt,
        "is_anomaly": 1,
        "risk_category": "Suspicious wording",
        "risk_severity": "Medium",
        "risk_score": 0.75,
        "detected_risk_signals": "SUSPICIOUS_WORDING_FLAG|HIGH_RISK_NARRATION_KEYWORD",
        "audit_explanation": f"Suspicious wording detected: Transaction description contains high-risk audit keyword '{word}'."
    })
    txn_id_counter += 1

# 12. Round-number or last-digit manipulation (80 txns)
round_amts = [50000.0, 100000.0, 250000.0, 500000.0, 1000000.0, 2000000.0]
for _ in range(80):
    t_id = f"TXN{txn_id_counter:06d}"
    t_date = random_date_in_range()
    amt = float(random.choice(round_amts))
    emp = EMPLOYEES[6]
    dept = DEPARTMENTS[3]
    v = random.choice(VENDORS[:5])
    
    records.append({
        "transaction_id": t_id,
        "transaction_date": str(t_date),
        "transaction_time": random_time_business(),
        "entry_type": "Automated ERP Entry",
        "general_ledger_account": "Consulting & Professional Fees",
        "amount": amt,
        "currency": "INR",
        "vendor_id": v['vendor_id'],
        "vendor_name": v['vendor_name'],
        "invoice_id": f"INV-RND-{random.randint(1000, 9999)}",
        "employee_id": emp['employee_id'],
        "employee_name": emp['employee_name'],
        "department_id": dept['department_id'],
        "department_name": dept['department_name'],
        "approved_by_id": "EMP003",
        "approved_by_name": "Priya Patel",
        "payment_mode": "NEFT",
        "description": f"Lump sum fee payment of ₹{int(amt):,} without itemized invoice breakdown",
        "ocr_extracted_amount": amt,
        "receipt_claimed_amount": amt,
        "is_anomaly": 1,
        "risk_category": "Round-number or last-digit manipulation",
        "risk_severity": "Medium",
        "risk_score": 0.72,
        "detected_risk_signals": "ROUND_NUMBER_MANIPULATION|ZERO_DECIMAL_PADDING",
        "audit_explanation": f"Round-number anomaly: Exact round payment of ₹{int(amt):,} lacking detailed itemized billing."
    })
    txn_id_counter += 1

# 13. Unusual amount (80 txns)
for _ in range(80):
    t_id = f"TXN{txn_id_counter:06d}"
    t_date = random_date_in_range()
    amt = round(float(random.randint(850000, 2400000)), 2) # Routine office supplies is ~5k-30k normally!
    emp = EMPLOYEES[8]
    dept = DEPARTMENTS[0]
    
    records.append({
        "transaction_id": t_id,
        "transaction_date": str(t_date),
        "transaction_time": random_time_business(),
        "entry_type": "Automated ERP Entry",
        "general_ledger_account": "Office Supplies",
        "amount": amt,
        "currency": "INR",
        "vendor_id": "VEN008",
        "vendor_name": "J2 Office Supplies Pvt Ltd",
        "invoice_id": f"INV-OUT-{random.randint(1000, 9999)}",
        "employee_id": emp['employee_id'],
        "employee_name": emp['employee_name'],
        "department_id": dept['department_id'],
        "department_name": dept['department_name'],
        "approved_by_id": "EMP003",
        "approved_by_name": "Priya Patel",
        "payment_mode": "RTGS",
        "description": "Bulk purchase order for routine office stationary paper and pens",
        "ocr_extracted_amount": amt,
        "receipt_claimed_amount": amt,
        "is_anomaly": 1,
        "risk_category": "Unusual amount",
        "risk_severity": "High",
        "risk_score": 0.86,
        "detected_risk_signals": "STATISTICAL_ZSCORE_OUTLIER|UNUSUAL_AMOUNT_FOR_ACCOUNT",
        "audit_explanation": f"Unusual amount risk: ₹{amt:,.2f} is an extreme 6+ sigma outlier for the Office Supplies ledger account."
    })
    txn_id_counter += 1

# 14. High monetary value (80 txns)
for _ in range(80):
    t_id = f"TXN{txn_id_counter:06d}"
    t_date = random_date_in_range()
    amt = round(float(random.randint(35000000, 95000000)), 2) # ₹3.5 Cr to ₹9.5 Cr!
    emp = EMPLOYEES[1] # CFO
    dept = DEPARTMENTS[0]
    v = VENDORS[4] # Larsen & Toubro
    
    records.append({
        "transaction_id": t_id,
        "transaction_date": str(t_date),
        "transaction_time": random_time_business(),
        "entry_type": "Automated ERP Entry",
        "general_ledger_account": "Raw Materials Procurement",
        "amount": amt,
        "currency": "INR",
        "vendor_id": v['vendor_id'],
        "vendor_name": v['vendor_name'],
        "invoice_id": f"INV-HIGH-{random.randint(1000, 9999)}",
        "employee_id": emp['employee_id'],
        "employee_name": emp['employee_name'],
        "department_id": dept['department_id'],
        "department_name": dept['department_name'],
        "approved_by_id": "EMP001",
        "approved_by_name": "Rajesh Subramanian",
        "payment_mode": "RTGS",
        "description": "Turnkey plant expansion infrastructure capital project disbursement",
        "ocr_extracted_amount": amt,
        "receipt_claimed_amount": amt,
        "is_anomaly": 1,
        "risk_category": "High monetary value",
        "risk_severity": "High",
        "risk_score": 0.83,
        "detected_risk_signals": "TOP_PERCENTILE_VALUE|C_SUITE_MANDATORY_REVIEW",
        "audit_explanation": f"High monetary value: Top 0.1% percentile disbursement of ₹{amt:,.2f} requiring mandatory board audit validation."
    })
    txn_id_counter += 1

# 15. Rare flow (80 txns)
for _ in range(80):
    t_id = f"TXN{txn_id_counter:06d}"
    t_date = random_date_in_range()
    v = VENDORS[6] # Apex Travel Solutions
    amt = round(float(random.randint(450000, 1800000)), 2)
    emp = EMPLOYEES[7]
    dept = DEPARTMENTS[2]
    
    records.append({
        "transaction_id": t_id,
        "transaction_date": str(t_date),
        "transaction_time": random_time_business(),
        "entry_type": "Automated ERP Entry",
        "general_ledger_account": "Raw Materials Procurement", # RARE FLOW: Travel vendor paid out of Raw Materials account!
        "amount": amt,
        "currency": "INR",
        "vendor_id": v['vendor_id'],
        "vendor_name": v['vendor_name'],
        "invoice_id": f"INV-RARE-{random.randint(1000, 9999)}",
        "employee_id": emp['employee_id'],
        "employee_name": emp['employee_name'],
        "department_id": dept['department_id'],
        "department_name": dept['department_name'],
        "approved_by_id": "EMP003",
        "approved_by_name": "Priya Patel",
        "payment_mode": "NEFT",
        "description": "Procurement of raw material steel billets from travel agency vendor",
        "ocr_extracted_amount": amt,
        "receipt_claimed_amount": amt,
        "is_anomaly": 1,
        "risk_category": "Rare flow",
        "risk_severity": "High",
        "risk_score": 0.85,
        "detected_risk_signals": "RARE_ACCOUNT_VENDOR_PAIRING|MISCLASSIFIED_EXPENSE_FLOW",
        "audit_explanation": f"Rare flow risk: Unprecedented pairing of travel vendor {v['vendor_name']} with Raw Materials general ledger account."
    })
    txn_id_counter += 1

# 16. Unusual flow (80 txns)
for _ in range(80):
    t_id = f"TXN{txn_id_counter:06d}"
    t_date = random_date_in_range()
    v = VENDORS[8] # Modern Stationers (normally ~₹5,000)
    amt = round(float(random.randint(1200000, 3500000)), 2) # ₹12 Lakhs to ₹35 Lakhs!
    emp = EMPLOYEES[8]
    dept = DEPARTMENTS[4]
    
    records.append({
        "transaction_id": t_id,
        "transaction_date": str(t_date),
        "transaction_time": random_time_business(),
        "entry_type": "Automated ERP Entry",
        "general_ledger_account": "Office Supplies",
        "amount": amt,
        "currency": "INR",
        "vendor_id": v['vendor_id'],
        "vendor_name": v['vendor_name'],
        "invoice_id": f"INV-FLOW-{random.randint(1000, 9999)}",
        "employee_id": emp['employee_id'],
        "employee_name": emp['employee_name'],
        "department_id": dept['department_id'],
        "department_name": dept['department_name'],
        "approved_by_id": "EMP003",
        "approved_by_name": "Priya Patel",
        "payment_mode": "RTGS",
        "description": f"Massive volume paper supply contract payout to routine stationary vendor",
        "ocr_extracted_amount": amt,
        "receipt_claimed_amount": amt,
        "is_anomaly": 1,
        "risk_category": "Unusual flow",
        "risk_severity": "High",
        "risk_score": 0.86,
        "detected_risk_signals": "UNUSUAL_FLOW_SPIKE|VENDOR_HISTORICAL_DEVIATION",
        "audit_explanation": f"Unusual flow risk: Disbursement of ₹{amt:,.2f} is 100x larger than historical average payment for vendor {v['vendor_name']}."
    })
    txn_id_counter += 1

# 17. Sequence gaps (80 txns)
for _ in range(80):
    t_id = f"TXN{txn_id_counter:06d}"
    t_date = random_date_in_range()
    v = VENDORS[5] # Blue Dart Express
    gap_inv = f"INV-BD-999{random.randint(500, 999)}" # Sequence jump from 100 to 999
    amt = round(float(random.randint(45000, 220000)), 2)
    emp = EMPLOYEES[11]
    dept = DEPARTMENTS[4]
    
    records.append({
        "transaction_id": t_id,
        "transaction_date": str(t_date),
        "transaction_time": random_time_business(),
        "entry_type": "Automated ERP Entry",
        "general_ledger_account": "Logistics & Freight",
        "amount": amt,
        "currency": "INR",
        "vendor_id": v['vendor_id'],
        "vendor_name": v['vendor_name'],
        "invoice_id": gap_inv,
        "employee_id": emp['employee_id'],
        "employee_name": emp['employee_name'],
        "department_id": dept['department_id'],
        "department_name": dept['department_name'],
        "approved_by_id": "EMP009",
        "approved_by_name": "Sneha Reddy",
        "payment_mode": "NEFT",
        "description": f"Express cargo courier dispatch payment for invoice {gap_inv}",
        "ocr_extracted_amount": amt,
        "receipt_claimed_amount": amt,
        "is_anomaly": 1,
        "risk_category": "Sequence gaps",
        "risk_severity": "Medium",
        "risk_score": 0.74,
        "detected_risk_signals": "INVOICE_SEQUENCE_GAP|FLOATING_REFERENCE_NUMBER",
        "audit_explanation": f"Sequence gap anomaly: Invoice reference {gap_inv} skips 800+ numbers in sequential vendor billing pattern."
    })
    txn_id_counter += 1

# 18. Reversal risk (80 txns)
for _ in range(80):
    t_id = f"TXN{txn_id_counter:06d}"
    t_date = random_date_in_range()
    amt = -1 * round(float(random.randint(350000, 1500000)), 2)
    emp = EMPLOYEES[7]
    dept = DEPARTMENTS[0]
    
    records.append({
        "transaction_id": t_id,
        "transaction_date": str(t_date),
        "transaction_time": random_time_business(),
        "entry_type": "Credit Note / Reversal",
        "general_ledger_account": "Consulting & Professional Fees",
        "amount": amt,
        "currency": "INR",
        "vendor_id": "VEN002",
        "vendor_name": "Tata Consultancy Services Ltd",
        "invoice_id": f"CN-UNLINKED-{random.randint(1000, 9999)}",
        "employee_id": emp['employee_id'],
        "employee_name": emp['employee_name'],
        "department_id": dept['department_id'],
        "department_name": dept['department_name'],
        "approved_by_id": "EMP002",
        "approved_by_name": "Vikram Malhotra",
        "payment_mode": "Manual Journal Entry",
        "description": "Unlinked credit note reversal clearing prior posted consulting fees without original invoice link",
        "ocr_extracted_amount": 0.0,
        "receipt_claimed_amount": 0.0,
        "is_anomaly": 1,
        "risk_category": "Reversal risk",
        "risk_severity": "High",
        "risk_score": 0.84,
        "detected_risk_signals": "UNLINKED_CREDIT_NOTE|REVERSAL_WITHOUT_ORIGINAL_REF",
        "audit_explanation": f"Reversal risk: Reversal credit note of ₹{abs(amt):,.2f} posted without reference to original transaction ID."
    })
    txn_id_counter += 1

# 19. Missing information / unintentional errors (80 txns)
for _ in range(80):
    t_id = f"TXN{txn_id_counter:06d}"
    t_date = random_date_in_range()
    emp = EMPLOYEES[12]
    dept = DEPARTMENTS[2]
    
    records.append({
        "transaction_id": t_id,
        "transaction_date": str(t_date),
        "transaction_time": random_time_business(),
        "entry_type": "Automated ERP Entry",
        "general_ledger_account": "Miscellaneous & Adjustments",
        "amount": 0.0, # Zero amount error
        "currency": "INR",
        "vendor_id": "",
        "vendor_name": "", # Missing vendor
        "invoice_id": "", # Missing invoice ID
        "employee_id": emp['employee_id'],
        "employee_name": emp['employee_name'],
        "department_id": dept['department_id'],
        "department_name": dept['department_name'],
        "approved_by_id": "EMP004",
        "approved_by_name": "Amit Sharma",
        "payment_mode": "NEFT",
        "description": "", # Empty description
        "ocr_extracted_amount": 0.0,
        "receipt_claimed_amount": 0.0,
        "is_anomaly": 1,
        "risk_category": "Missing information / unintentional errors",
        "risk_severity": "Medium",
        "risk_score": 0.70,
        "detected_risk_signals": "MISSING_VENDOR|ZERO_AMOUNT|EMPTY_DESCRIPTION",
        "audit_explanation": "Data integrity error: Transaction recorded with zero amount, blank vendor, and empty narration."
    })
    txn_id_counter += 1

# 20. Weekend and after-hours posting (80 txns)
for _ in range(80):
    t_id = f"TXN{txn_id_counter:06d}"
    t_date = random_date_in_range()
    # Force Sunday
    while t_date.weekday() != 6:
        t_date += datetime.timedelta(days=1)
    t_time = random_time_after_hours() # 2 AM
    amt = round(float(random.randint(180000, 950000)), 2)
    emp = EMPLOYEES[10]
    dept = DEPARTMENTS[3]
    v = VENDORS[1]
    
    records.append({
        "transaction_id": t_id,
        "transaction_date": str(t_date),
        "transaction_time": t_time,
        "entry_type": "Manual Journal Entry",
        "general_ledger_account": "Consulting & Professional Fees",
        "amount": amt,
        "currency": "INR",
        "vendor_id": v['vendor_id'],
        "vendor_name": v['vendor_name'],
        "invoice_id": f"INV-WKD-{random.randint(1000, 9999)}",
        "employee_id": emp['employee_id'],
        "employee_name": emp['employee_name'],
        "department_id": dept['department_id'],
        "department_name": dept['department_name'],
        "approved_by_id": "EMP007",
        "approved_by_name": "Rahul Sharma",
        "payment_mode": "NEFT",
        "description": f"Sunday midnight manual approval entry for vendor payment",
        "ocr_extracted_amount": amt,
        "receipt_claimed_amount": amt,
        "is_anomaly": 1,
        "risk_category": "Weekend and after-hours posting",
        "risk_severity": "Medium",
        "risk_score": 0.76,
        "detected_risk_signals": "WEEKEND_POSTING|AFTER_HOURS_TIMESTAMP",
        "audit_explanation": f"Weekend / after-hours posting: Transaction authorized on Sunday at {t_time} outside normal business operating window."
    })
    txn_id_counter += 1

# 21. Complex structure risk (80 txns)
v_offshore = VENDORS[14] # Global Offshore Holdings BVI
terms = ["Cayman SPV Transfer", "BVI Offshore Holdings", "Intercompany License Sub-allocation", "Special Purpose Entity Fee"]
for _ in range(80):
    t_id = f"TXN{txn_id_counter:06d}"
    t_date = random_date_in_range()
    term = random.choice(terms)
    amt = round(float(random.randint(2500000, 12000000)), 2)
    emp = EMPLOYEES[2] # VP Finance
    dept = DEPARTMENTS[0]
    
    records.append({
        "transaction_id": t_id,
        "transaction_date": str(t_date),
        "transaction_time": random_time_business(),
        "entry_type": "Automated ERP Entry",
        "general_ledger_account": "Consulting & Professional Fees",
        "amount": amt,
        "currency": "INR",
        "vendor_id": v_offshore['vendor_id'],
        "vendor_name": v_offshore['vendor_name'],
        "invoice_id": f"INV-OFF-{random.randint(1000, 9999)}",
        "employee_id": emp['employee_id'],
        "employee_name": emp['employee_name'],
        "department_id": dept['department_id'],
        "department_name": dept['department_name'],
        "approved_by_id": "EMP002",
        "approved_by_name": "Vikram Malhotra",
        "payment_mode": "Wire Transfer",
        "description": f"Cross-border remittance for {term} intellectual property management",
        "ocr_extracted_amount": amt,
        "receipt_claimed_amount": amt,
        "is_anomaly": 1,
        "risk_category": "Complex structure risk",
        "risk_severity": "Critical",
        "risk_score": 0.93,
        "detected_risk_signals": "OFFSHORE_ENTITY_TAX_HAVEN|COMPLEX_STRUCTURE_TERMS",
        "audit_explanation": f"Complex structure risk: Payment of ₹{amt:,.2f} remitted to offshore entity {v_offshore['vendor_name']} involving '{term}' structure."
    })
    txn_id_counter += 1

# 22. Complex financial-instrument risk (80 txns)
fin_terms = ["currency derivative swap option", "interest rate hedge settlement", "structured note forward contract", "fx option premium payout"]
for _ in range(80):
    t_id = f"TXN{txn_id_counter:06d}"
    t_date = random_date_in_range()
    term = random.choice(fin_terms)
    amt = round(float(random.randint(1800000, 8500000)), 2)
    emp = EMPLOYEES[1] # CFO
    dept = DEPARTMENTS[0]
    
    records.append({
        "transaction_id": t_id,
        "transaction_date": str(t_date),
        "transaction_time": random_time_business(),
        "entry_type": "Manual Journal Entry",
        "general_ledger_account": "Financial Instruments & Derivatives",
        "amount": amt,
        "currency": "INR",
        "vendor_id": "",
        "vendor_name": "Financial Counterparty Bank",
        "invoice_id": f"DERIV-{random.randint(1000, 9999)}",
        "employee_id": emp['employee_id'],
        "employee_name": emp['employee_name'],
        "department_id": dept['department_id'],
        "department_name": dept['department_name'],
        "approved_by_id": "EMP001",
        "approved_by_name": "Rajesh Subramanian",
        "payment_mode": "RTGS",
        "description": f"OTC derivative settlement payout for {term}",
        "ocr_extracted_amount": 0.0,
        "receipt_claimed_amount": 0.0,
        "is_anomaly": 1,
        "risk_category": "Complex financial-instrument risk",
        "risk_severity": "High",
        "risk_score": 0.88,
        "detected_risk_signals": "DERIVATIVE_COMPLEX_INSTRUMENT|OTC_HEDGE_SETTLEMENT",
        "audit_explanation": f"Complex financial instrument risk: OTC derivative payment of ₹{amt:,.2f} involving '{term}' requiring specialized treasury audit."
    })
    txn_id_counter += 1

# 23. Benford’s Law anomalies (80 txns)
# Generate amounts starting predominantly with 7, 8, or 9 (violating logarithmic distribution)
for _ in range(80):
    t_id = f"TXN{txn_id_counter:06d}"
    t_date = random_date_in_range()
    first_digit = random.choice([7, 8, 9])
    remainder = random.randint(1000, 9999)
    amt = float(f"{first_digit}{remainder}.00")
    emp = EMPLOYEES[8]
    dept = DEPARTMENTS[0]
    v = random.choice(VENDORS[:5])
    
    records.append({
        "transaction_id": t_id,
        "transaction_date": str(t_date),
        "transaction_time": random_time_business(),
        "entry_type": "Automated ERP Entry",
        "general_ledger_account": "Miscellaneous & Adjustments",
        "amount": amt,
        "currency": "INR",
        "vendor_id": v['vendor_id'],
        "vendor_name": v['vendor_name'],
        "invoice_id": f"INV-BEN-{random.randint(1000, 9999)}",
        "employee_id": emp['employee_id'],
        "employee_name": emp['employee_name'],
        "department_id": dept['department_id'],
        "department_name": dept['department_name'],
        "approved_by_id": "EMP003",
        "approved_by_name": "Priya Patel",
        "payment_mode": "NEFT",
        "description": f"Adjusted billing payout for miscellaneous operational expenses",
        "ocr_extracted_amount": amt,
        "receipt_claimed_amount": amt,
        "is_anomaly": 1,
        "risk_category": "Benford's Law anomalies",
        "risk_severity": "Medium",
        "risk_score": 0.77,
        "detected_risk_signals": "BENFORDS_LAW_DEVIATION|HIGH_DIGIT_FREQUENCY_SPIKE",
        "audit_explanation": f"Benford's Law anomaly: Cohort exhibits statistically significant over-representation of leading digits 7, 8, and 9."
    })
    txn_id_counter += 1

# 24. ML-based unknown or emerging risk (80 txns)
for _ in range(80):
    t_id = f"TXN{txn_id_counter:06d}"
    t_date = random_date_in_range()
    amt = round(float(random.randint(125000, 890000) + 0.37), 2)
    emp = EMPLOYEES[13]
    dept = DEPARTMENTS[1]
    v = VENDORS[2]
    
    records.append({
        "transaction_id": t_id,
        "transaction_date": str(t_date),
        "transaction_time": random_time_business(),
        "entry_type": "Automated ERP Entry",
        "general_ledger_account": "Facilities & Utilities",
        "amount": amt,
        "currency": "INR",
        "vendor_id": v['vendor_id'],
        "vendor_name": v['vendor_name'],
        "invoice_id": f"INV-ML-{random.randint(1000, 9999)}",
        "employee_id": emp['employee_id'],
        "employee_name": emp['employee_name'],
        "department_id": dept['department_id'],
        "department_name": dept['department_name'],
        "approved_by_id": "EMP003",
        "approved_by_name": "Priya Patel",
        "payment_mode": "NEFT",
        "description": "Routine utility maintenance payout with non-standard multi-dimensional behavioral signature",
        "ocr_extracted_amount": amt,
        "receipt_claimed_amount": amt,
        "is_anomaly": 1,
        "risk_category": "ML-based unknown or emerging risk",
        "risk_severity": "High",
        "risk_score": 0.89,
        "detected_risk_signals": "AUTOENCODER_HIGH_RECONSTRUCTION_ERROR|ISOLATION_FOREST_OUTLIER",
        "audit_explanation": "ML-based emerging risk: Deep Autoencoder + Isolation Forest ensemble model flagged entry due to anomalous latent cluster distance."
    })
    txn_id_counter += 1

# 25. Expense receipt mismatch (80 txns)
for _ in range(80):
    t_id = f"TXN{txn_id_counter:06d}"
    t_date = random_date_in_range()
    ocr_val = round(float(random.randint(3500, 8500)), 2)
    claimed_val = ocr_val * random.choice([5.0, 8.0, 10.0]) # E.g. Claimed ₹48,500 for receipt of ₹4,850!
    emp = EMPLOYEES[14]
    dept = DEPARTMENTS[6]
    
    records.append({
        "transaction_id": t_id,
        "transaction_date": str(t_date),
        "transaction_time": random_time_business(),
        "entry_type": "Expense Claim",
        "general_ledger_account": "Travel & Entertainment",
        "amount": claimed_val,
        "currency": "INR",
        "vendor_id": "",
        "vendor_name": "Hotel / Restaurant Receipt",
        "invoice_id": f"CLM-MIS-{random.randint(10000, 99999)}",
        "employee_id": emp['employee_id'],
        "employee_name": emp['employee_name'],
        "department_id": dept['department_id'],
        "department_name": dept['department_name'],
        "approved_by_id": "EMP010",
        "approved_by_name": "Kiran Rao",
        "payment_mode": "Credit Card",
        "description": f"Client dinner travel expense claim reimbursement submission",
        "ocr_extracted_amount": ocr_val,
        "receipt_claimed_amount": claimed_val,
        "is_anomaly": 1,
        "risk_category": "Expense receipt mismatch",
        "risk_severity": "High",
        "risk_score": 0.91,
        "detected_risk_signals": "OCR_AMOUNT_MISMATCH|CLAIM_OVERSTATEMENT",
        "audit_explanation": f"Expense receipt mismatch: Claimed amount ₹{claimed_val:,.2f} differs significantly from OCR receipt value ₹{ocr_val:,.2f}."
    })
    txn_id_counter += 1


# ----------------------------------------------------
# 3. BUILD DATAFRAME & SHUFFLE
# ----------------------------------------------------

df_joined = pd.DataFrame(records)

# Shuffle rows so anomalies are mixed with safe transactions
df_joined = df_joined.sample(frac=1, random_state=42).reset_index(drop=True)

# Re-assign sequential transaction_id
for idx, row in df_joined.iterrows():
    df_joined.at[idx, 'transaction_id'] = f"TXN{idx+1:06d}"

# Save CSV, Parquet, and JSON files to data/ and auditData/
csv_path_data = os.path.join(DATA_DIR, "audit_anomalies_joined_dataset.csv")
json_path_data = os.path.join(DATA_DIR, "audit_anomalies_joined_dataset.json")
csv_path_audit = os.path.join(AUDIT_DATA_DIR, "audit_anomalies_joined_dataset.csv")

df_joined.to_csv(csv_path_data, index=False)
df_joined.to_json(json_path_data, orient="records", indent=2)
df_joined.to_csv(csv_path_audit, index=False)

print(f"\nSuccessfully generated Master Joined Dataset!")
print(f"Total Transactions: {len(df_joined)}")
print(f"Safe Transactions: {(df_joined['is_anomaly'] == 0).sum()}")
print(f"Anomaly Transactions: {(df_joined['is_anomaly'] == 1).sum()}")
print(f"\nBreakdown by Risk Category:")
print(df_joined['risk_category'].value_counts())
print(f"\nFiles exported:")
print(f"- {csv_path_data}")
print(f"- {json_path_data}")
print(f"- {csv_path_audit}")
