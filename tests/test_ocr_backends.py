"""
Unit tests for ocr/backends.py OCR engine abstractions.
"""
import unittest
import numpy as np
from ocr.enums import OCRStatus
from ocr.exceptions import OCRBackendError
from ocr.backends import AbstractOCRBackend, MockOCRBackend, TesseractBackend


class TestOCRBackends(unittest.TestCase):
    """Test suite for OCR backend engine abstractions."""

    def setUp(self):
        """Create synthetic test image array for OCR backend testing."""
        self.test_image = np.zeros((100, 200, 3), dtype=np.uint8)

    def test_mock_ocr_backend(self):
        """Test MockOCRBackend execution and OCRResult output."""
        mock_backend = MockOCRBackend(
            mock_text="PARACETAMOL 500mg BATCH-2026",
            mock_confidence=0.97,
        )
        self.assertEqual(mock_backend.get_backend_name(), "MockOCRBackend")

        result = mock_backend.extract_text(self.test_image)
        self.assertEqual(result.raw_text, "PARACETAMOL 500mg BATCH-2026")
        self.assertEqual(result.average_confidence, 0.97)
        self.assertGreater(result.processing_time_ms, 0.0)

    def test_invalid_image_raises_ocr_backend_error(self):
        """Test passing invalid non-array input raises OCRBackendError."""
        mock_backend = MockOCRBackend()
        with self.assertRaises(OCRBackendError):
            mock_backend.extract_text(None)

    def test_abstract_backend_instantiation_raises_type_error(self):
        """Test that attempting to instantiate AbstractOCRBackend directly raises TypeError."""
        with self.assertRaises(TypeError):
            AbstractOCRBackend()


if __name__ == "__main__":
    unittest.main()
