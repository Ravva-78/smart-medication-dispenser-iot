"""
Unit tests for ocr/verifier.py OCR verification engine.
"""
import unittest
from ocr.enums import OCRStatus
from ocr.models import MedicineIdentity
from ocr.verifier import OCRVerifier


class TestOCRVerifier(unittest.TestCase):
    """Test suite for OCRVerifier prescription matching and verification engine."""

    def setUp(self):
        """Create sample MedicineIdentity fixtures for verification testing."""
        self.valid_identity = MedicineIdentity(
            medicine_name="Paracetamol",
            strength="500mg",
            dosage_form="Tablet",
            batch_number="BATCH-2026-09",
            expiry_date="2028-12-31",
            manufacturer="PharmaCorp",
            confidence=0.9500,
        )

        self.mismatched_identity = MedicineIdentity(
            medicine_name="Aspirin",
            strength="100mg",
            dosage_form="Tablet",
            confidence=0.9200,
        )

        self.low_conf_identity = MedicineIdentity(
            medicine_name="Paracetamol",
            strength="500mg",
            dosage_form="Tablet",
            confidence=0.4500,
        )

    def test_verify_matching_prescription(self):
        """Test verification passes cleanly for matching medicine name and strength."""
        status, reason = OCRVerifier.verify(
            extracted=self.valid_identity,
            expected_name="Paracetamol",
            expected_strength="500mg",
        )
        self.assertEqual(status, OCRStatus.VERIFIED)
        self.assertIn("Match successful", reason)

    def test_verify_mismatched_medicine_name(self):
        """Test verification rejects when extracted drug name contradicts expected prescription."""
        status, reason = OCRVerifier.verify(
            extracted=self.mismatched_identity,
            expected_name="Paracetamol",
            expected_strength="500mg",
        )
        self.assertEqual(status, OCRStatus.REJECTED)
        self.assertIn("Medicine mismatch", reason)

    def test_verify_mismatched_strength(self):
        """Test verification rejects when drug name matches but strength differs."""
        diff_strength_id = MedicineIdentity(
            medicine_name="Paracetamol",
            strength="650mg",
            confidence=0.95,
        )
        status, reason = OCRVerifier.verify(
            extracted=diff_strength_id,
            expected_name="Paracetamol",
            expected_strength="500mg",
        )
        self.assertEqual(status, OCRStatus.REJECTED)
        self.assertIn("Strength mismatch", reason)

    def test_verify_low_confidence_uncertain(self):
        """Test verification returns UNCERTAIN when confidence is below threshold."""
        status, reason = OCRVerifier.verify(
            extracted=self.low_conf_identity,
            expected_name="Paracetamol",
            expected_strength="500mg",
            min_confidence=0.70,
        )
        self.assertEqual(status, OCRStatus.UNCERTAIN)
        self.assertIn("Low confidence", reason)


if __name__ == "__main__":
    unittest.main()
