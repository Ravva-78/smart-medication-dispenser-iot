"""
Unit and API integration tests for FastAPI application layer (app/main.py).
"""
import unittest
from fastapi.testclient import TestClient
from app.main import app


class TestFastAPIApplication(unittest.TestCase):
    """Test suite for FastAPI REST API endpoints."""

    def setUp(self):
        """Initialize FastAPI TestClient."""
        self.client = TestClient(app)

    def test_health_check_endpoint(self):
        """Test GET /api/v1/health via FastAPI TestClient."""
        response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["status"], "HEALTHY")

    def test_openapi_schema_generation(self):
        """Test GET /openapi.json generates valid OpenAPI 3.0 specification."""
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        schema = response.json()
        self.assertIn("openapi", schema)
        self.assertEqual(schema["info"]["title"], "Autonomous Medicine Dispenser Platform API")

    def test_inspect_and_evaluate_fastapi_endpoint(self):
        """Test POST /api/v1/inspect endpoint via FastAPI TestClient."""
        payload = {
            "strip_id": "strip_fastapi_100",
            "raw_inspection": {
                "inspection_id": "insp_fa_01",
                "image_name": "frame.jpg",
                "capture_time": "2026-07-29T12:00:00Z",
                "camera_id": "cam_01",
                "total": 10,
                "present": 10,
                "missing": 0,
                "missing_indices": [],
                "avg_confidence": 0.98,
            },
            "prescription": {
                "prescription_id": "rx_fa_01",
                "patient_id": "patient_fa_55",
                "medicine_name": "Paracetamol",
                "strength": "500mg",
            }
        }
        response = self.client.post("/api/v1/inspect", json=payload)
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertTrue(res_data["success"])
        self.assertIn("decision", res_data["data"])


if __name__ == "__main__":
    unittest.main()
