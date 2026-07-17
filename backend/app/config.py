"""
AuditAI — Centralized configuration.

Reads settings from environment variables with sensible defaults for local development.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file for local development
load_dotenv()

# === Paths ===
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent  # AuditAI/
BACKEND_ROOT = PROJECT_ROOT / "backend"
DATA_DIR = PROJECT_ROOT / "data"
RECEIPTS_DIR = DATA_DIR / "receipts"
SROIE_DIR = DATA_DIR / "sroie"
TRAINED_MODELS_DIR = BACKEND_ROOT / "trained_models"
UPLOAD_DIR = PROJECT_ROOT / "uploads"

# Ensure critical directories exist
for d in [DATA_DIR, RECEIPTS_DIR, TRAINED_MODELS_DIR, UPLOAD_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# === Database ===
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost:5433/postgres")

# === Gemini LLM ===
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# === OCR ===
# Primary OCR engine: "paddleocr" or "tesseract"
OCR_PRIMARY_ENGINE = os.getenv("OCR_PRIMARY_ENGINE", "paddleocr")
TESSERACT_CMD = os.getenv("TESSERACT_CMD", "tesseract")  # Path to tesseract binary

# === ML Pipeline ===
# Autoencoder hyperparameters
AE_LATENT_DIM = int(os.getenv("AE_LATENT_DIM", "16"))
AE_EPOCHS = int(os.getenv("AE_EPOCHS", "100"))
AE_LEARNING_RATE = float(os.getenv("AE_LEARNING_RATE", "0.001"))
AE_BATCH_SIZE = int(os.getenv("AE_BATCH_SIZE", "64"))

# Isolation Forest hyperparameters
IF_CONTAMINATION = float(os.getenv("IF_CONTAMINATION", "0.07"))
IF_N_ESTIMATORS = int(os.getenv("IF_N_ESTIMATORS", "200"))
IF_RANDOM_STATE = int(os.getenv("IF_RANDOM_STATE", "42"))

# Scoring combination weights
# final_score = SCORE_ALPHA * reconstruction_error + (1 - SCORE_ALPHA) * isolation_forest_score
# Alpha is set lower (0.4) because the Isolation Forest already operates on the
# reconstructed feature space, so it implicitly captures reconstruction quality.
# The reconstruction error adds a direct signal for gross distortions.
SCORE_ALPHA = float(os.getenv("SCORE_ALPHA", "0.4"))
FRAUD_SCORE_THRESHOLD = float(os.getenv("FRAUD_SCORE_THRESHOLD", "0.60"))

# === Feature Engineering ===
AMOUNT_MISMATCH_THRESHOLD = float(os.getenv("AMOUNT_MISMATCH_THRESHOLD", "0.05"))
DUPLICATE_SIMILARITY_THRESHOLD = float(os.getenv("DUPLICATE_SIMILARITY_THRESHOLD", "0.85"))
VENDOR_ANOMALY_THRESHOLD = float(os.getenv("VENDOR_ANOMALY_THRESHOLD", "0.3"))

# Known approved vendors — loaded from DB at runtime, this is the fallback static list
KNOWN_VENDORS = [
    "Amazon", "Walmart", "Starbucks", "Uber", "Lyft", "Delta Airlines",
    "United Airlines", "Marriott", "Hilton", "FedEx", "UPS", "Staples",
    "Office Depot", "Best Buy", "Apple", "Microsoft", "Google", "Zomato",
    "Swiggy", "Ola", "MakeMyTrip", "IRCTC", "Flipkart", "Reliance",
    "Tata Consultancy Services", "Infosys", "Wipro", "HCL Technologies",
]

# Indian public holidays (2025-2026) for weekend/holiday feature
HOLIDAYS = [
    "2025-01-26", "2025-03-14", "2025-03-31", "2025-04-06", "2025-04-10",
    "2025-04-14", "2025-04-18", "2025-05-01", "2025-05-12", "2025-06-07",
    "2025-07-06", "2025-08-15", "2025-08-16", "2025-08-27", "2025-09-05",
    "2025-10-02", "2025-10-20", "2025-10-21", "2025-10-23", "2025-11-01",
    "2025-11-05", "2025-12-25",
    "2026-01-26", "2026-03-03", "2026-03-20", "2026-03-30", "2026-04-03",
    "2026-04-14", "2026-05-01", "2026-05-16", "2026-08-15", "2026-08-25",
    "2026-10-02", "2026-10-10", "2026-11-14", "2026-12-25",
]

# === API ===
API_V1_PREFIX = "/api/v1"
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
