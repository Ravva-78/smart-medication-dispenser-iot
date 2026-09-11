"""
Unit tests for ocr/parser.py medical entity extraction parser.
"""
import unittest
from ocr.parser import OCREntityParser
from ocr.models import MedicineIdentity


class TestOCREntityParser(unittest.TestCase):
    """Test suite for OCREntityParser entity extraction and regex parsing."""

    def test_extract_medicine_name(self):
        """Test matching known drug names from cleaned OCR text."""
        name, conf = OCREntityParser.extract_name("PARACETAMOL 500mg TABLETS")
        self.assertEqual(name, "Paracetamol")
        self.assertGreater(conf, 0.90)

        name_lower, conf_lower = OCREntityParser.extract_name("amoxicillin 250 mg capsules")
        self.assertEqual(name_lower, "Amoxicillin")

    def test_extract_strength(self):
        """Test regex extraction of dosage strength."""
        str1, conf1 = OCREntityParser.extract_strength("PARACETAMOL 500mg TABLETS")
        self.assertEqual(str1, "500mg")

        str2, conf2 = OCREntityParser.extract_strength("AMOXICILLIN 250 mg CAPSULES")
        self.assertEqual(str2, "250mg")

        str3, conf3 = OCREntityParser.extract_strength("SOLUTIONS 10mg/5ml")
        self.assertEqual(str3, "10mg/5ml")

    def test_extract_batch_and_expiry(self):
        """Test extracting manufacturing batch number and expiry date."""
        text = "PARACETAMOL 500mg BATCH-2026-09 EXP 12/2028"
        batch, b_conf = OCREntityParser.extract_batch_number(text)
        self.assertEqual(batch, "BATCH-2026-09")

        exp, e_conf = OCREntityParser.extract_expiry_date(text)
        self.assertEqual(exp, "2028-12-31")

    def test_full_parse_to_medicine_identity(self):
        """Test parsing full raw text into a structured MedicineIdentity object."""
        text = "PARACETAMOL 500mg TABLETS BATCH-2026-09 EXP 12/2028 PHARMACORP"
        identity = OCREntityParser.parse(text)
        self.assertIsInstance(identity, MedicineIdentity)
        self.assertEqual(identity.medicine_name, "Paracetamol")
        self.assertEqual(identity.strength, "500mg")
        self.assertEqual(identity.dosage_form, "Tablet")
        self.assertEqual(identity.batch_number, "BATCH-2026-09")
        self.assertEqual(identity.expiry_date, "2028-12-31")
        self.assertGreater(identity.confidence, 0.85)


if __name__ == "__main__":
    unittest.main()
