"""
API Schema & Contract Locking Tests.

Purpose:
    Enforces strict backward-compatibility checks on FastAPI REST response payloads to ensure
    frontend developers receive guaranteed JSON schemas matching docs/API_SPECIFICATION.md.
"""

import unittest
from fastapi.testclient import TestClient
from app.main import app


class TestAPIContractLock(unittest.TestCase):
    """Test suite asserting JSON schema stability for frontend integration."""

    def setUp(self):
        self.client = TestClient(app)

    def test_health_endpoint_schema_contract(self):
        """Assert GET /api/v1/health conforms to exact API_SPECIFICATION contract."""
        res = self.client.get("/api/v1/health")
        self.assertEqual(res.status_code, 200)
        body = res.json()

        # Required Top-Level Keys
        self.assertIn("status_code", body)
        self.assertIn("success", body)
        self.assertIn("code", body)
        self.assertIn("data", body)
        self.assertIn("error_message", body)

        # Required Data Keys
        data = body["data"]
        self.assertIn("status", data)
        self.assertIn("version", data)
        self.assertIn("services", data)

    def test_inspect_endpoint_schema_contract(self):
        """Assert POST /api/v1/inspect conforms to exact API_SPECIFICATION contract."""
        payload = {
            "strip_id": "strip_lock_100",
            "raw_inspection": {
                "inspection_id": "insp_lock_01",
                "image_name": "frame.jpg",
                "capture_time": "2026-07-29T12:00:00Z",
                "camera_id": "cam_01",
                "total": 10,
                "present": 10,
                "missing": 0,
                "missing_indices": [],
                "avg_confidence": 0.99,
            },
            "prescription": {
                "prescription_id": "rx_lock_01",
                "patient_id": "patient_lock_10",
                "medicine_name": "Paracetamol",
                "strength": "500mg",
            }
        }
        res = self.client.post("/api/v1/inspect", json=payload)
        self.assertEqual(res.status_code, 200)
        body = res.json()

        data = body["data"]
        self.assertIn("strip_id", data)
        self.assertIn("inventory_state", data)
        self.assertIn("inventory_event", data)
        self.assertIn("decision", data)

        # Decision Contract Assertions
        decision = data["decision"]
        self.assertIn("decision_id", decision)
        self.assertIn("patient_id", decision)
        self.assertIn("outcome", decision)
        self.assertIn("reason", decision)
        self.assertIn("actionable", decision)
        self.assertIn("schema_version", decision)


if __name__ == "__main__":
    unittest.main()
