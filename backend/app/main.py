from contextlib import asynccontextmanager
import os
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.auth.security import get_current_user, require_roles
from backend.app.api.auth import router as auth_router
from backend.app.api.claims import router as claims_router
from backend.app.api.receipts import router as receipts_router
from backend.app.api.fraud import router as fraud_router
from backend.app.api.reports import router as reports_router
from backend.app.api.cases import router as cases_router
from backend.app.api.analytics import router as analytics_router
from backend.app.db import Base, engine


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Auth tables are additive, so existing claim data does not need migration.
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title="AuditAI API",
    description="Automated financial anomaly detection and ingestion pipeline.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv(
        "FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register endpoints
app.include_router(auth_router)
app.include_router(claims_router, dependencies=[Depends(get_current_user)])
app.include_router(receipts_router, dependencies=[Depends(get_current_user)])
app.include_router(fraud_router, dependencies=[Depends(require_roles("maker", "checker", "admin"))])
app.include_router(reports_router, dependencies=[Depends(require_roles("maker", "checker", "admin"))])
app.include_router(cases_router, dependencies=[Depends(get_current_user)])
app.include_router(analytics_router, dependencies=[Depends(require_roles("maker", "checker", "admin"))])

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
