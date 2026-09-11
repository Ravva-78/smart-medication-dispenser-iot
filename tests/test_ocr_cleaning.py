"""
Unit tests for ocr/cleaning.py text normalization module.
"""
import unittest
from ocr.cleaning import OCRTextCleaner


class TestOCRTextCleaner(unittest.TestCase):
    """Test suite for OCR raw text normalization and OCR character confusion correction."""

    def test_normalize_whitespace(self):
        """Test collapsing extra spaces, tabs, and newlines."""
        raw = "PARACETAMOL   500\nmg   BATCH\t\t-101"
        cleaned = OCRTextCleaner.normalize_whitespace(raw)
        self.assertEqual(cleaned, "PARACETAMOL 500 mg BATCH -101")

    def test_correct_ocr_character_confusion_digits(self):
        """Test correcting letter 'O' to digit '0' in numbers and strengths."""
        # 5OOmg -> 500mg
        raw = "PARACETAMOL 5OOmg EXP 2O28-12-31"
        corrected = OCRTextCleaner.correct_ocr_character_confusion(raw)
        self.assertIn("500mg", corrected)
        self.assertIn("2028-12-31", corrected)

    def test_correct_ocr_character_confusion_letters(self):
        """Test correcting digit '0' to letter 'O' in uppercase drug names."""
        raw = "PARACETAM0L 500mg"
        corrected = OCRTextCleaner.correct_ocr_character_confusion(raw)
        self.assertIn("PARACETAMOL", corrected)

    def test_full_clean_pipeline(self):
        """Test execution of full OCR text cleaning pipeline."""
        raw = "  PARACETAM0L \t 5OOmg \n EXP  2O28/12/31  "
        cleaned = OCRTextCleaner.clean(raw)
        self.assertEqual(cleaned, "PARACETAMOL 500mg EXP 2028/12/31")

    def test_empty_string_handling(self):
        """Test handling empty or whitespace-only inputs."""
        self.assertEqual(OCRTextCleaner.clean("   "), "")
        self.assertEqual(OCRTextCleaner.clean(None), "")


if __name__ == "__main__":
    unittest.main()
