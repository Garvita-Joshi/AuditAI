# Behavioral model v2 and OCR

The active API now uses `backend/app/ml/behavioral_pipeline.py` through the public `ml/pipeline.py` interface. The older autoencoder/isolation_forest modules are legacy and are not loaded by this API. A v2 bundle was trained on the 10,000-row joined synthetic benchmark and saved locally to `backend/trained_models/pipeline_v2.joblib`. Model binaries are git-ignored.

## Flow

Transactions + receipt extraction -> prior-only behavioral features -> train-fitted preprocessing -> independent AE and Isolation Forest -> fixed reference scaling -> frozen calibration threshold -> audit review.

- 32 numeric features adapted from notebook C: log absolute amounts and signs, historical deviations, rolling frequencies, capped lifetime counts, new/missing entities, duplicate and split-window evidence, and receipt availability/quality/mismatch signals. IDs are lookup keys, not model inputs. Category is a lookup group, not an arbitrary risk label.
- Complete ledger replay precedes selection of scoring targets. Scoring only pending claims does not lose earlier scored history. Rows sharing a timestamp cannot see each other; results preserve the caller's order. Company/entity namespaces separate histories.
- Database expense claims currently store a claim date but no transaction time. Date-only records use noon UTC only as a neutral ordering placeholder: they have no after-hours signal. Offline records with an explicit `event_time`, original `submitted_at`, or `transaction_date` plus `transaction_time` retain their actual hour. A bulk import timestamp does not reconstruct real historical availability. Calendar signals currently use UTC; align local business hours before production deployment.
- 60% normal training, 15% early stopping, 10% calibration, 15% final testing, split chronologically without dividing equal timestamps. AdamW, dropout, best-checkpoint restoration, and train-only standardization reduce avoidable fitting risk.
- Normal validation scores supply robust log-score reference scales with a floor. The separate calibration period supplies the F1 threshold if both labels exist, otherwise the 99th percentile of known-normal scores. Nothing is normalized against the inference batch.
- UI anomaly indices range from 0 to 100; 50 is the frozen review boundary. This is a monotonic representation of the continuous combined score, not a probability. Raw reconstruction MSE and raw IF anomaly score are stored separately. SHAP explains IF path-length evidence only, with sign oriented toward anomaly; it does not explain the entire combined model.

## Train and use

## Source-data format

For the normal application upload, the minimum CSV columns are:

```text
claim_id,employee_id,employee_name,claimed_amount,vendor_name,claimed_date
```

These columns are required. `category`, `description`, `submitted_at`, `entity_id`, and `is_fraud`/`is_anomaly` are optional. Amounts may contain commas or `₹`/`$`; dates should be unambiguous ISO values such as `2026-03-31`.

The project also accepts the benchmark transaction naming used by `audit_anomalies_joined_dataset.csv` through these mappings:

| Source column | Application meaning |
|---|---|
| `transaction_id` | `claim_id` |
| `amount` | `claimed_amount` |
| `transaction_date` | `claimed_date` |
| `general_ledger_account` | `category` |
| `is_anomaly` | `is_fraud` (benchmark label only) |
| `risk_category` | `fraud_type` (context only) |
| `ocr_extracted_amount` | `ocr_amount` |
| `extracted_vendor` | `ocr_vendor` |
| `extracted_date` | `ocr_date` |
| `extraction_confidence` | `ocr_confidence` (0 to 1) |

OCR columns are optional. You may upload receipts separately instead; the receipt endpoint stores the raw OCR result and links it to the claim. If OCR is in the CSV, include `ocr_amount` plus `ocr_confidence` when available. Blank confidence remains unknown; do not fill it with `1.0`.

The model does not need `transaction_id`, `vendor_id`, or `employee_id` as numeric/model columns. It uses the vendor and employee values as lookup keys to calculate prior history. Keep those identifiers in the source when available. Do not include generated columns such as `risk_score`, `detected_risk_signals`, `audit_explanation`, or an existing combined anomaly score as model inputs.

For training a labeled benchmark, provide `is_fraud` or `is_anomaly` with `0/1` or `false/true` and run with explicit trust of those labels. For real production training, leave labels unknown until reviewed cases exist; an absent label is not automatically a normal transaction. The CLI training script requires `--trust-labels` so this choice cannot happen accidentally.

Examples already present in this project are [expense_claims.csv](../data/expense_claims.csv) and [audit_anomalies_joined_dataset.csv](../auditData/audit_anomalies_joined_dataset.csv).

```powershell
python scripts/train_behavioral_model.py --csv auditData/audit_anomalies_joined_dataset.csv --trust-labels
python -m uvicorn backend.app.main:app --reload --port 8000
```

The training command writes the bundle and `training_report.json`. A fresh interpreter reloads the complete preprocessing, weights, score references, schema and decision threshold from one atomically replaced file. Old model files are preserved and cannot be accidentally mixed into v2.

API:

- `GET /api/v1/fraud/model`: readiness, feature names and training metadata.
- `POST /api/v1/fraud/train`: trains using closed reviewed cases. Unreviewed default-false flags are unknown, not normal. The review decision is a proxy label; verify it represents actual anomaly adjudication before using it as truth.
- `POST /api/v1/fraud/train?trust_synthetic_labels=true`: explicitly trusts the database's synthetic `is_fraud` labels. Use only for benchmark/demo data. Requires at least five known normals in each development period and at least 50 total records.
- `POST /api/v1/fraud/score`: scores pending/processing claims.
- `POST /api/v1/fraud/score?rescore=true`: refreshes open scored/flagged claims as well. Closed approved/rejected claims are preserved. Existing cases are preserved even if a refreshed score is lower; the workflow decision remains an auditor's responsibility.

The local benchmark run (one seed) produced AP 0.9630, precision 0.8963, recall 0.8701 and F1 0.8830 on 1,500 test rows. These are synthetic benchmark results, not real-world fraud accuracy. This implementation changes features and partitioning relative to the notebook ablation, so the numbers are not an isolated head-to-head improvement claim. Multi-period, unseen-entity and reviewed real-data evaluation remain necessary before production use.

## OCR

`rapidocr-onnxruntime==1.4.4` supplies CPU OCR with bundled models; optional PaddleOCR/Tesseract fallbacks remain. For Tesseract, set `TESSERACT_CMD` to its executable. RapidOCR's API reference: https://rapidai.github.io/RapidOCRDocs/v1.4.4/install_usage/api/RapidOCR/

Upload images or a single-page PDF through the existing receipt upload control and select the claim ID. PDFium renders PDFs locally. Original pixels go to OCR first; thresholded images are only a fallback. Multi-page PDFs are rejected as failed rather than silently ignoring later pages. Structured extraction runs locally without an LLM call.

- Empty/failed extraction is reported as failed, never processed.
- Stored quality is the lower of recognition confidence and field completeness; it is a heuristic, not a calibrated correctness probability. Amount mismatches below the configured quality floor (default 0.6) are suppressed, with separate missing/low-quality indicators.
- Imported `ocr_amount`/`ocr_extracted_amount` columns are retained, with unknown confidence explicitly marked. They are assumed supplied by an upstream extraction process, not independently verified by this import.
- Attaching a receipt invalidates an open claim's previous prediction and marks it pending. Use Run Scoring to refresh it. Existing closed decisions remain closed.
- Original images/raw text remain available as review evidence; no fraud decision should depend on an OCR mismatch alone.

## Verification

`python -m pytest tests -q` covers future-data invariance, identity renaming, equal timestamps, target ordering, signed amounts, low-confidence OCR, model reload, batch-independent scores, database history during scoring, repeated rescoring, receipt invalidation, CSV receipt amounts and real image/PDF OCR. Two existing SROIE placeholders skip because that dataset is absent. `npm run build` in frontend validates the UI changes.

Model deployment limitations: historical replay currently uses the receipt extraction stored today; true retrospective evaluation needs versioned OCR/master-data snapshots and label availability timestamps. Full replay is suitable for this project size, but large ledgers should persist incremental history with the same score-before-update semantics. This model flags duplicate/split evidence but is not a substitute for a dedicated audit rules engine.
