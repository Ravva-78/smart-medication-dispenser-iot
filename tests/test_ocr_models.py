"""
Unit tests for ocr/models.py and ocr/enums.py domain contracts.
"""
import unittest
from dataclasses import FrozenInstanceError
from ocr.enums import OCRStatus, ExtractionField
from ocr.exceptions import OCRError, InvalidOCRDataError, LowConfidenceOCRError
from ocr.models import MedicineIdentity, OCRRegion, OCRResult


class TestOCRDomainContracts(unittest.TestCase):
    """Test suite for OCR Subsystem domain dataclasses and enums."""

    def setUp(self):
        """Create sample MedicineIdentity, OCRRegion, and OCRResult fixtures."""
        self.identity = MedicineIdentity(
            medicine_name="Paracetamol",
            strength="500mg",
            dosage_form="Tablet",
            batch_number="BATCH-2026-09",
            expiry_date="2028-12-31",
            manufacturer="PharmaCorp",
            confidence=0.9850,
        )

        self.region1 = OCRRegion(bbox=(10, 20, 100, 50), text="PARACETAMOL", confidence=0.99)
        self.region2 = OCRRegion(bbox=(10, 60, 80, 80), text="500 mg", confidence=0.98)

        self.ocr_result = OCRResult(
            raw_text="PARACETAMOL 500 mg BATCH-2026-09 EXP 12/2028",
            extracted_regions=(self.region1, self.region2),
            identity=self.identity,
            average_confidence=0.9850,
            processing_time_ms=42.5,
            status=OCRStatus.VERIFIED,
        )

    def test_medicine_identity_immutability_and_serialization(self):
        """Test MedicineIdentity frozen immutability and dictionary roundtrip."""
        self.assertEqual(self.identity.medicine_name, "Paracetamol")
        self.assertEqual(self.identity.strength, "500mg")
        self.assertEqual(self.identity.confidence, 0.9850)

        with self.assertRaises(FrozenInstanceError):
            self.identity.medicine_name = "Aspirin"

        d = self.identity.to_dict()
        self.assertEqual(d["medicine_name"], "Paracetamol")
        self.assertEqual(d["strength"], "500mg")

        reconstructed = MedicineIdentity.from_dict(d)
        self.assertEqual(reconstructed, self.identity)

    def test_ocr_result_serialization_roundtrip(self):
        """Test OCRResult dictionary roundtrip serialization."""
        d = self.ocr_result.to_dict()
        self.assertEqual(d["status"], "VERIFIED")
        self.assertEqual(d["average_confidence"], 0.985)
        self.assertEqual(len(d["extracted_regions"]), 2)

        reconstructed = OCRResult.from_dict(d)
        self.assertEqual(reconstructed, self.ocr_result)
        self.assertEqual(reconstructed.identity, self.identity)

    def test_ocr_exceptions(self):
        """Test domain exceptions hierarchy."""
        self.assertTrue(issubclass(InvalidOCRDataError, OCRError))
        self.assertTrue(issubclass(LowConfidenceOCRError, OCRError))


if __name__ == "__main__":
    unittest.main()
