"""
Unit tests for ocr/preprocessing.py image preprocessor.
"""
import unittest
import numpy as np
import cv2
from ocr.preprocessing import OCRImagePreprocessor


class TestOCRImagePreprocessor(unittest.TestCase):
    """Test suite for OCR image preprocessing computer vision utilities."""

    def setUp(self):
        """Create sample synthetic image arrays for image processing verification."""
        # 3-channel BGR synthetic image (100x100 pixels)
        self.bgr_image = np.zeros((100, 100, 3), dtype=np.uint8)
        cv2.putText(self.bgr_image, "PARACETAMOL", (5, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

        # Grayscale synthetic image
        self.gray_image = cv2.cvtColor(self.bgr_image, cv2.COLOR_BGR2GRAY)

    def test_to_grayscale(self):
        """Test converting 3-channel BGR image to single channel grayscale."""
        gray = OCRImagePreprocessor.to_grayscale(self.bgr_image)
        self.assertEqual(gray.ndim, 2)
        self.assertEqual(gray.shape, (100, 100))

        # Passing grayscale should return directly
        gray_passthrough = OCRImagePreprocessor.to_grayscale(self.gray_image)
        self.assertEqual(gray_passthrough.ndim, 2)

    def test_apply_clahe(self):
        """Test contrast enhancement via CLAHE histogram equalization."""
        enhanced = OCRImagePreprocessor.apply_clahe(self.gray_image)
        self.assertEqual(enhanced.shape, (100, 100))
        self.assertEqual(enhanced.dtype, np.uint8)

    def test_denoise_and_sharpen(self):
        """Test noise reduction and unsharp masking functions."""
        denoised = OCRImagePreprocessor.denoise(self.gray_image)
        self.assertEqual(denoised.shape, (100, 100))

        sharpened = OCRImagePreprocessor.sharpen(self.gray_image)
        self.assertEqual(sharpened.shape, (100, 100))

    def test_binarize(self):
        """Test adaptive/Otsu binarization output."""
        binary = OCRImagePreprocessor.binarize(self.gray_image)
        self.assertEqual(binary.ndim, 2)
        # Binarized pixel values should be 0 or 255
        unique_vals = set(np.unique(binary))
        self.assertTrue(unique_vals.issubset({0, 255}))

    def test_full_preprocess_pipeline(self):
        """Test full sequential preprocessing pipeline execution."""
        clean_img = OCRImagePreprocessor.preprocess(self.bgr_image)
        self.assertEqual(clean_img.shape, (100, 100))
        self.assertEqual(clean_img.ndim, 2)
        self.assertEqual(clean_img.dtype, np.uint8)

    def test_invalid_image_type_raises_value_error(self):
        """Test that passing None or non-array raises ValueError."""
        with self.assertRaises(ValueError):
            OCRImagePreprocessor.preprocess(None)


if __name__ == "__main__":
    unittest.main()
