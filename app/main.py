"""
FastAPI Application Entry Point.

Purpose:
    Exposes production REST API endpoints with automatic OpenAPI 3.0 interactive documentation (/docs).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.server import DispenserAPIService
from app.schemas import InspectRequestSchema, StandardAPIResponseSchema

app = FastAPI(
    title="Autonomous Medicine Dispenser Platform API",
    description="Production REST API service providing camera frame inspection, inventory tracking, OCR packaging verification, and clinical compliance decision evaluation.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for React frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Singleton API Service facade instance
api_service = DispenserAPIService()


@app.get("/api/v1/health", response_model=StandardAPIResponseSchema, tags=["Health"])
def health_check():
    """GET /api/v1/health system readiness probe."""
    res = api_service.health()
    return res.to_dict()


@app.post("/api/v1/inspect", response_model=StandardAPIResponseSchema, tags=["Inspection"])
def inspect_and_evaluate(req: InspectRequestSchema):
    """POST /api/v1/inspect process camera frame and evaluate clinical compliance."""
    res = api_service.process_inspection_and_evaluate(
        raw_inspection=req.raw_inspection.model_dump(),
        prescription=req.prescription.model_dump(),
        strip_id=req.strip_id,
    )
    return res.to_dict()


@app.get("/api/v1/clinical/metrics/{patient_id}", response_model=StandardAPIResponseSchema, tags=["Clinical"])
def get_patient_metrics(patient_id: str):
    """GET /api/v1/clinical/metrics/{patient_id} patient adherence stats."""
    res = api_service.get_patient_metrics(patient_id)
    return res.to_dict()


@app.get("/api/v1/alerts/{patient_id}", response_model=StandardAPIResponseSchema, tags=["Alerting"])
def get_alert_history(patient_id: str):
    """GET /api/v1/alerts/{patient_id} dispatched caregiver notifications."""
    res = api_service.get_alert_history(patient_id)
    return res.to_dict()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
