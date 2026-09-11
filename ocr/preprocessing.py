"""
OCR Verification Subsystem Image Preprocessor.

Purpose:
    Provides computer vision image pre-processing operations to optimize text legibility on medicine packaging and foil backings.

Responsibilities:
    - Grayscale conversion.
    - CLAHE (Contrast Limited Adaptive Histogram Equalization) for glare/reflection mitigation.
    - Bilateral / Gaussian denoising.
    - Adaptive & Otsu threshold binarization.
    - Unsharp mask sharpening.
    - Full pipeline execution (`preprocess`).

Dependencies:
    - `opencv-python` (`cv2`), `numpy`.
"""

import cv2
import numpy as np
from typing import Tuple, Optional


class OCRImagePreprocessor:
    """Computer vision preprocessor for optimizing packaging images prior to OCR extraction."""

    @staticmethod
    def to_grayscale(image: np.ndarray) -> np.ndarray:
        """Convert BGR image array to single-channel grayscale."""
        if image is None or not isinstance(image, np.ndarray):
            raise ValueError("Input image must be a valid non-None numpy ndarray.")
        if image.ndim == 2:
            return image
        if image.ndim == 3 and image.shape[2] == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        if image.ndim == 3 and image.shape[2] == 4:
            return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
        raise ValueError(f"Unsupported image shape for grayscale conversion: {image.shape}")

    @staticmethod
    def apply_clahe(
        image: np.ndarray,
        clip_limit: float = 2.0,
        tile_grid_size: Tuple[int, int] = (8, 8)
    ) -> np.ndarray:
        """Enhance local contrast and reduce foil specular glare using CLAHE."""
        gray = OCRImagePreprocessor.to_grayscale(image)
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
        return clahe.apply(gray)

    @staticmethod
    def denoise(image: np.ndarray, h: float = 10.0) -> np.ndarray:
        """Reduce image noise while preserving text boundary edges using Fast NlMeans Denoising."""
        gray = OCRImagePreprocessor.to_grayscale(image)
        return cv2.fastNlMeansDenoising(gray, None, h=h, templateWindowSize=7, searchWindowSize=21)

    @staticmethod
    def sharpen(image: np.ndarray) -> np.ndarray:
        """Sharpen character edges using unsharp masking."""
        gray = OCRImagePreprocessor.to_grayscale(image)
        blurred = cv2.GaussianBlur(gray, (0, 0), 3)
        sharpened = cv2.addWeighted(gray, 1.5, blurred, -0.5, 0)
        return sharpened

    @staticmethod
    def binarize(image: np.ndarray) -> np.ndarray:
        """Apply Otsu thresholding to produce crisp high-contrast black-and-white image."""
        gray = OCRImagePreprocessor.to_grayscale(image)
        # Apply Gaussian blur before Otsu thresholding
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary

    @classmethod
    def preprocess(cls, image: np.ndarray) -> np.ndarray:
        """
        Execute full sequential preprocessing pipeline:
        Grayscale -> CLAHE Contrast -> Denoise -> Sharpen -> Binarize.

        Args:
            image: BGR or Grayscale numpy image array.

        Returns:
            Preprocessed 2D grayscale/binary numpy image array.
        """
        if image is None or not isinstance(image, np.ndarray):
            raise ValueError("Input image must be a valid non-None numpy ndarray.")

        gray = cls.to_grayscale(image)
        clahe_img = cls.apply_clahe(gray)
        sharpened = cls.sharpen(clahe_img)
        binary = cls.binarize(sharpened)
        return binary


__all__ = ["OCRImagePreprocessor"]
