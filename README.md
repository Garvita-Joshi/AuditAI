# AuditAI

> **AI-powered financial fraud detection system for enterprise audit teams.**

AuditAI is a full-stack financial anomaly detection platform built for audit firms, banks, and large corporates. It combines OCR receipt parsing, a two-stage ML pipeline (PyTorch Autoencoder + Scikit-learn Isolation Forest), SHAP explainability, and Gemini-powered audit report generation into a single, demoable v1.

---

## 🚀 Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | FastAPI (Python) |
| **Frontend** | React + Vite |
| **Database** | PostgreSQL |
| **ML** | PyTorch (Autoencoder), Scikit-learn (Isolation Forest), SHAP |
| **OCR** | PaddleOCR (primary), Pytesseract (fallback) |
| **LLM** | Google Gemini API |

---

## 🧠 What It Detects (v1: Employee Expense Fraud)

- **Typosquatting vendors** (e.g. "Zomto Food" vs "Zomato")
- **Duplicate claims** (fuzzy-matched by vendor + amount + date)
- **Amount inflation** (OCR receipt vs. claimed amount mismatch)
- **Split transactions** (multiple claims on same date from same employee)
- **Weekend/holiday claims**
- **Round-number anomalies**
- **Related-party transactions**
- **Benford's Law deviations**
- **Segregation of Duties violations**

---

## 📐 ML Architecture

```
Raw Expense Claims
      ↓
Feature Engineering (15 features per claim)
      ↓
Stage 1: PyTorch Autoencoder → Reconstruction Error
      ↓
Stage 2: Isolation Forest (on reconstructed features) → Anomaly Score
      ↓
Combined Score = 0.4 × Recon Error + 0.6 × IF Score
      ↓
SHAP Explainability → Gemini Audit Report Generation
```

---

## 🏗️ Project Structure

```
AuditAI/
├── backend/
│   └── app/
│       ├── api/           # FastAPI routers (claims, fraud, cases, analytics, reports)
│       ├── models/        # SQLAlchemy ORM models
│       ├── schemas/       # Pydantic request/response schemas
│       ├── features/      # Feature engineering (15 fraud signals)
│       ├── ml/            # Autoencoder, Isolation Forest, SHAP pipeline
│       ├── ocr/           # PaddleOCR + Tesseract dual-engine
│       ├── llm/           # Gemini API integration
│       └── config.py      # Centralized hyperparameters
├── frontend/
│   └── src/
│       ├── pages/         # Dashboard, Upload, ClaimsTable, ClaimDetail, AuditScreens
│       ├── components/    # Navbar, StatCard, ScoreBadge, ShapChart, ScoreGauge, etc.
│       └── api/           # Axios API client
├── scripts/
│   ├── generate_expense_claims.py   # Synthetic data generator
│   └── seed_and_train.py            # One-command pipeline setup
└── data/                            # Generated CSVs and synthetic receipts
```

---

## ⚡ Quick Start

### 1. Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL (running on port 5433)

### 2. Install backend dependencies
```bash
pip install fastapi uvicorn sqlalchemy psycopg2-binary pandas numpy torch scikit-learn shap fuzzywuzzy python-Levenshtein python-multipart google-generativeai pillow opencv-python-headless
```

### 3. Set environment variables
```bash
export DATABASE_URL="postgresql://localhost:5433/postgres"
export GEMINI_API_KEY="your-gemini-api-key"
```

### 4. Start the backend
```bash
python -m uvicorn backend.app.main:app --reload --port 8000
```

### 5. Seed the database + train models
```bash
python scripts/seed_and_train.py
```

### 6. Start the frontend
```bash
cd frontend && npm install && npm run dev
```

Open **http://localhost:5173** to see the dashboard.

---

## 📊 Dashboard Features

- **Audit Dashboard** — KPI metrics, monthly flagged claims bar chart, score distribution
- **High-Risk Claims Queue** — Filter by case status, risk level, and keyword search
- **Inline Typosquat Warnings** — Hover tooltips showing `⚠ 89% match to 'Domino's Pizza'`
- **3-Tier Risk Colors** — Amber (50-70%), Orange (70-85%), Red (85%+)
- **Claim Detail** — OCR results, SHAP waterfall chart, score gauges, AI audit report
- **Maker-Checker Workflow** — Makers recommend, Checkers sign off, append-only trail
- **Audit Screens** — Benford's Law chart, Related-Party screening, SoD violations

---

## 🔑 Key API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/claims/upload` | Upload CSV of expense claims |
| `GET` | `/api/v1/claims` | List claims with filters and pagination |
| `POST` | `/api/v1/fraud/train` | Train ML pipeline |
| `POST` | `/api/v1/fraud/score` | Score all claims |
| `GET` | `/api/v1/fraud/summary` | Dashboard statistics |
| `GET` | `/api/v1/analytics/benford` | Benford's Law distribution |
| `GET` | `/api/v1/analytics/related-parties` | Related-party screen |
| `GET` | `/api/v1/analytics/sod-violations` | SoD violations |
| `POST` | `/api/v1/cases/{id}/maker-recommend` | Maker recommendation |
| `POST` | `/api/v1/cases/{id}/checker-signoff` | Checker final sign-off |

---

## 📄 License

MIT
