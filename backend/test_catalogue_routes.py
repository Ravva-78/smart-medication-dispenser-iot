"""
Read-only access to the SYNTHETIC test-medicine catalogue (qa_testing/test_catalogue/synthetic_catalogue.json).
Every entry is marked TEST DATA. Nothing here touches the database or the real medicine catalogue.

    GET /api/v1/test-catalogue
"""
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

CATALOGUE_PATH = Path(__file__).resolve().parent.parent / "qa_testing" / "test_catalogue" / "synthetic_catalogue.json"

router = APIRouter(prefix="/api/v1", tags=["Test data"])


@router.get("/test-catalogue")
def get_test_catalogue():
    try:
        return json.loads(CATALOGUE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        raise HTTPException(status_code=500, detail=f"Test catalogue unavailable: {err}")
