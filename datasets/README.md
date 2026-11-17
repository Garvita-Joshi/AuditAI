# AuditAI Datasets & Demonstration Guide

This directory contains all datasets used for **training**, **evaluation**, and **interactive demonstration** of AuditAI's fraud detection and procurement capabilities.

---

## Folder Structure

```
datasets/
├── training_datasets/                     # Core corpora used to train the ML Autoencoder & Isolation Forest
│   ├── audit_anomalies_joined_dataset.csv # 10,000+ joined ERP enterprise transaction training corpus
│   ├── ml_ready_transactions.csv          # Feature-engineered 34-signal vector space
│   ├── transactions.csv                   # Raw historical financial transactions
│   ├── fraud_labels.csv                   # Historical audit risk ground-truth labels
│   ├── aster_4000_claims_training_corpus.csv # 4,000 synthetic employee expense claims
│   ├── aster_anomaly_labels.csv           # Ground truth anomaly tags
│   ├── employees.csv                      # Staff baseline profiles
│   ├── vendors.csv                        # Vendor registry baseline
│   └── departments.csv                    # Organizational cost centers
│
└── test_demo_datasets/                    # Ready-to-upload demonstration test files for each test case
    ├── 01_expense_claims/                 # Upload at: /upload (Claims Ingestion)
    │   ├── test_expense_claims_with_anomalies.csv (Triggers weekend spending, threshold splitting, receipt mismatch)
    │   └── sample_standard_claims.csv     (Normal baseline claims)
    │
    ├── 02_vendor_master/                  # Upload at: /audit-screens (Master Reference Import)
    │   ├── test_vendor_master_with_ghost_vendors.csv (Planted duplicate banks, fake GSTINs, shell vendors)
    │   └── sample_standard_vendor_master.csv (Verified vendor registry)
    │
    ├── 03_employee_roster/                # Upload at: /audit-screens (HR Roster Import)
    │   ├── test_employee_roster_with_collusion_keys.csv (Includes employee bank accounts matching vendors: B_vendor == B_emp)
    │   └── sample_standard_employee_roster.csv (Clean HR directory)
    │
    ├── 04_payroll_payments/               # Upload at: /audit-screens (Payroll Import)
    │   ├── test_payroll_payments_ghost_employees.csv (Payments to exited employees and before-joining dates)
    │   └── sample_standard_payroll_payments.csv (Standard verified payroll)
    │
    ├── 05_bank_transfers_circular/        # Upload at: /audit-screens (Circular Payments Graph)
    │   ├── test_bank_transfers_circular_loops.csv (Triggers 3-entity circular money laundering loop: A -> B -> C -> A)
    │   └── sample_standard_bank_transfers.csv (Standard linear transfers)
    │
    └── 06_invoice_receipt_images_pdf/     # Upload at: /upload or /procurement/invoice-review
        ├── sample_procurement_invoice.pdf (Enterprise PO 3-way matching PDF invoice)
        ├── makemytrip_invoice_sample.png  (Corporate travel bill)
        ├── metro_bites_receipt_sample.png (Dining receipt for OCR extraction)
        ├── receipt_AST-DEMO-CLM-001.png   (Matching receipt: INR 4,500)
        ├── receipt_AST-DEMO-CLM-002.png   (Planted mismatch: INR 4,500 receipt vs INR 45,000 claim)
        └── receipt_AST-DEMO-CLM-003.png   (Matching receipt: INR 6,000)
```

---

## How to Demonstrate Each Use Case

### Case 1: Real-time Expense Anomaly & Receipt Mismatch
* **Where to Upload:** Navigate to `http://localhost:5173/upload`.
* **File to Upload:** `test_demo_datasets/01_expense_claims/test_expense_claims_with_anomalies.csv`.
* **What to Show:**
  1. The claims are uploaded and scored in real-time.
  2. Claim `AST-DEMO-CLM-002` will trigger an **orange/red anomaly badge** due to amount variance.
  3. Upload `receipt_AST-DEMO-CLM-002.png` into the receipt section for `AST-DEMO-CLM-002`.
  4. The OCR engine reads `INR 4,500` off the bill and flags an immediate **10x receipt mismatch** against the claimed `INR 45,000`.

### Case 2: Ghost Vendors & Internal Collusion Screening
* **Where to Upload:** Navigate to `http://localhost:5173/claims` -> Click **Master Reference Data & Ingestion**.
* **Files to Upload:**
  1. Step 1: Upload `test_demo_datasets/02_vendor_master/test_vendor_master_with_ghost_vendors.csv`.
  2. Step 2: Upload `test_demo_datasets/03_employee_roster/test_employee_roster_with_collusion_keys.csv`.
* **What to Show:**
  * Open any claim (or view Claim Details).
  * The **Master Reference Data & Internal Collusion Screening** engine flags:
    * **`B_vendor == B_emp` Account Collision:** An employee's personal salary bank account matches the vendor payment bank account!
    * **Ghost Vendor Flag:** Vendor lacks registered GSTIN/PAN in corporate ground truth.

### Case 3: Circular Shell-Company Kickbacks (Network Graph)
* **Where to Upload:** Navigate to `http://localhost:5173/audit-screens` -> Select **Circular Payments**.
* **File to Upload:** `test_demo_datasets/05_bank_transfers_circular/test_bank_transfers_circular_loops.csv`.
* **What to Show:**
  * The interactive network graph constructs directed edges between accounts.
  * AuditAI instantly detects the closed cycle (`AST-DEMO-CYCLE-01 -> AST-DEMO-CYCLE-02 -> AST-DEMO-CYCLE-03 -> AST-DEMO-CYCLE-01`) highlighted in red, proving shell-company fund circularity.

### Case 4: Ghost Employee Payroll Leakage
* **Where to Upload:** Navigate to `http://localhost:5173/audit-screens` -> Select **Payroll Reconciliation**.
* **File to Upload:** `test_demo_datasets/04_payroll_payments/test_payroll_payments_ghost_employees.csv`.
* **What to Show:**
  * Detects payroll disbursed to employees after their termination date and unauthorized salary escalations exceeding approved baseline bands.

### Case 5: 3-Way Matching & Procurement Invoice PDF OCR
* **Where to Upload:** Navigate to `http://localhost:5173/procurement` -> Open an active purchase request -> Upload Final Invoice.
* **File to Upload:** `test_demo_datasets/06_invoice_receipt_images_pdf/sample_procurement_invoice.pdf`.
* **What to Show:**
  * RapidOCR parses multi-page invoice line-items, checks unit prices and quantities against the awarded PO, runs the hybrid Autoencoder + Isolation Forest score, and unlocks 1-click **PayPal Sandbox Escrow Settlement**.
