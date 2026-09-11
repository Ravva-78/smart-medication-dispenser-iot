"""
Unit tests for backend API controllers and service facade (backend/controllers.py, backend/server.py).
"""
import unittest
import numpy as np
from datetime import datetime, timezone
from backend.enums import HTTPStatusCode
from backend.models import APIResponse
from backend.server import DispenserAPIService


class TestBackendAPI(unittest.TestCase):
    """Test suite for Backend API service facade and controllers."""

    def setUp(self):
        """Initialize API service facade instance."""
        self.api_service = DispenserAPIService()
        self.now = datetime(2026, 7, 29, 12, 0, 0, tzinfo=timezone.utc)
        self.crop_image = np.zeros((100, 200, 3), dtype=np.uint8)

    def test_health_check_endpoint(self):
        """Test GET /api/v1/health returns HTTP 200 OK and system status."""
        response = self.api_service.health()
        self.assertEqual(response.status_code, HTTPStatusCode.OK.value)
        self.assertTrue(response.success)
        self.assertEqual(response.data["status"], "HEALTHY")

    def test_inspect_and_evaluate_endpoint_flow(self):
        """Test POST /api/v1/inspect end-to-end API execution flow."""
        prescription = {
            "prescription_id": "rx_api_100",
            "patient_id": "patient_api_42",
            "medicine_name": "Paracetamol",
            "strength": "500mg",
        }

        # Baseline inspection 1 (10 present)
        raw_insp_1 = {
            "inspection_id": "insp_api_01",
            "image_name": "frame1.jpg",
            "capture_time": self.now.isoformat(),
            "camera_id": "cam_01",
            "total": 10,
            "present": 10,
            "missing": 0,
            "missing_indices": [],
            "avg_confidence": 0.99,
        }

        self.api_service.process_inspection_and_evaluate(
            raw_inspection=raw_insp_1,
            prescription=prescription,
            strip_id="strip_api_99",
        )

        # Inspection 2 (1 tablet removed)
        raw_insp_2 = {
            "inspection_id": "insp_api_02",
            "image_name": "frame2.jpg",
            "capture_time": self.now.isoformat(),
            "camera_id": "cam_01",
            "total": 10,
            "present": 9,
            "missing": 1,
            "missing_indices": [2],
            "avg_confidence": 0.99,
        }

        response = self.api_service.process_inspection_and_evaluate(
            raw_inspection=raw_insp_2,
            prescription=prescription,
            strip_id="strip_api_99",
            image_array=self.crop_image,
        )

        self.assertEqual(response.status_code, HTTPStatusCode.OK.value)
        self.assertTrue(response.success)
        self.assertIn("decision", response.data)
        self.assertEqual(response.data["decision"]["outcome"], "CORRECT_DOSE")


    def test_get_patient_metrics_endpoint(self):
        """Test GET /api/v1/clinical/metrics/{patient_id} query."""
        response = self.api_service.get_patient_metrics("patient_api_42")
        self.assertEqual(response.status_code, HTTPStatusCode.OK.value)
        self.assertEqual(response.data["patient_id"], "patient_api_42")


if __name__ == "__main__":
    unittest.main()
