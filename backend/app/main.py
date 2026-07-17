from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api.claims import router as claims_router
from backend.app.api.receipts import router as receipts_router
from backend.app.api.fraud import router as fraud_router
from backend.app.api.reports import router as reports_router
from backend.app.api.cases import router as cases_router
from backend.app.api.analytics import router as analytics_router

app = FastAPI(
    title="AuditAI API",
    description="Automated financial anomaly detection and ingestion pipeline.",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register endpoints
app.include_router(claims_router)
app.include_router(receipts_router)
app.include_router(fraud_router)
app.include_router(reports_router)
app.include_router(cases_router)
app.include_router(analytics_router)

@app.get("/")
def read_root():
    return {
        "app": "AuditAI",
        "description": "Financial Transaction Anomaly Detection & Ingestion Engine",
        "version": "1.0.0",
        "status": "healthy"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
