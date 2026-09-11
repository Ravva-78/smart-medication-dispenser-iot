"""
Unit tests for ocr/manager.py OCRManager orchestrator facade.
"""
import unittest
import numpy as np
from ocr.enums import OCRStatus
from ocr.models import OCRResult, MedicineIdentity
from ocr.backends import MockOCRBackend
from ocr.manager import OCRManager


class TestOCRManager(unittest.TestCase):
    """Test suite for OCRManager orchestrator facade."""

    def setUp(self):
        """Set up OCRManager instance with MockOCRBackend."""
        self.mock_backend = MockOCRBackend(
            mock_text="PARACETAMOL 500mg TABLETS BATCH-2026-09 EXP 12/2028 PHARMACORP",
            mock_confidence=0.96,
        )
        self.manager = OCRManager(backend=self.mock_backend)
        self.synthetic_image = np.zeros((100, 200, 3), dtype=np.uint8)

    def test_process_image_flow(self):
        """Test full end-to-end OCR processing flow on an image array."""
        result = self.manager.process_image(self.synthetic_image, preprocess=True)

        self.assertIsInstance(result, OCRResult)
        self.assertEqual(result.status, OCRStatus.VERIFIED)
        self.assertIsNotNone(result.identity)
        self.assertEqual(result.identity.medicine_name, "Paracetamol")
        self.assertEqual(result.identity.strength, "500mg")
        self.assertEqual(result.identity.batch_number, "BATCH-2026-09")

    def test_verify_medicine_workflow(self):
        """Test verifying image against expected prescription requirements."""
        result, status, reason = self.manager.verify_medicine(
            image=self.synthetic_image,
            expected_name="Paracetamol",
            expected_strength="500mg",
        )
        self.assertEqual(status, OCRStatus.VERIFIED)
        self.assertIn("Match successful", reason)
        self.assertEqual(result.identity.medicine_name, "Paracetamol")

    def test_verify_medicine_rejection_workflow(self):
        """Test verification rejecting when expected medicine name contradicts extracted identity."""
        result, status, reason = self.manager.verify_medicine(
            image=self.synthetic_image,
            expected_name="Ibuprofen",
            expected_strength="400mg",
        )
        self.assertEqual(status, OCRStatus.REJECTED)
        self.assertIn("Medicine mismatch", reason)


if __name__ == "__main__":
    unittest.main()
