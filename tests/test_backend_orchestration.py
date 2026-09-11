"""
Backend Orchestration & REST API Integration Tests.

Purpose:
    Validates end-to-end device inspection requests via FastAPI and DispenserAPIService:
    Device DEV-001 -> Patient PAT-001 -> Prescription -> Subsystems -> Session Log Persistence.
"""

import unittest
from fastapi.testclient import TestClient
from backend.main import app
from database.connection import verify_connection


class TestBackendOrchestration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_root_and_health(self):
        """Test GET / and GET /api/v1/health."""
        r1 = self.client.get("/")
        self.assertEqual(r1.status_code, 200)
        self.assertIn("version", r1.json())

        r2 = self.client.get("/api/v1/health")
        self.assertEqual(r2.status_code, 200)
        self.assertTrue(r2.json()["success"])

    def test_02_get_patient_details(self):
        """Test GET /api/v1/patients/PAT-001."""
        r = self.client.get("/api/v1/patients/PAT-001")
        self.assertEqual(r.status_code, 200)
        data = r.json()["data"]
        self.assertEqual(data["patient_id"], "PAT-001")
        self.assertEqual(data["name"], "Ravi Kumar")

    def test_03_get_prescriptions(self):
        """Test GET /api/v1/patients/PAT-001/prescriptions."""
        r = self.client.get("/api/v1/patients/PAT-001/prescriptions")
        self.assertEqual(r.status_code, 200)
        rx_list = r.json()["data"]["prescriptions"]
        self.assertGreaterEqual(len(rx_list), 1)

    def test_04_device_inspection_session_correct_dose(self):
        """Test POST /api/v1/devices/DEV-001/inspection with correct tablet removal."""
        form_data = {
            "total_slots": "10",
            "missing_count": "1",
            "simulated_ocr_text": "PARACETAMOL 500mg BATCH-2026-09 EXP 12/2028",
        }
        r = self.client.post("/api/v1/devices/DEV-001/inspection", data=form_data)
        self.assertEqual(r.status_code, 200)
        data = r.json()["data"]
        self.assertIn("session_id", data)
        self.assertEqual(data["device_id"], "DEV-001")
        self.assertEqual(data["compliance_decision"]["outcome"], "CORRECT_DOSE")

    def test_05_device_inspection_session_wrong_medicine(self):
        """Test POST /api/v1/devices/DEV-002/inspection with wrong medicine OCR."""
        form_data = {
            "total_slots": "10",
            "missing_count": "1",
            "simulated_ocr_text": "IBUPROFEN 400mg BATCH-IB2026 EXP 05/2027",
        }
        r = self.client.post("/api/v1/devices/DEV-002/inspection", data=form_data)
        self.assertEqual(r.status_code, 200)
        data = r.json()["data"]
        self.assertEqual(data["device_id"], "DEV-002")
        self.assertEqual(data["compliance_decision"]["outcome"], "WRONG_MEDICINE")
        self.assertGreaterEqual(len(data["dispatched_alerts"]), 1)


if __name__ == "__main__":
    unittest.main()
