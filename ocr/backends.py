"""
OCR Verification Subsystem Engine Abstractions.

Purpose:
    Provides an abstract interface (`AbstractOCRBackend`) and concrete implementations
    (Mock, Tesseract, EasyOCR) for OCR text extraction.

Responsibilities:
    - Establish `AbstractOCRBackend(ABC)` contract (`extract_text`, `get_backend_name`).
    - Implement `MockOCRBackend` for deterministic offline testing.
    - Implement `TesseractBackend` wrapping PyTesseract with graceful fallbacks.
    - Handle image input validation and convert outputs to unified `OCRResult`.

Dependencies:
    - Standard library `abc`, `time`, `logging`, `typing`.
    - `numpy`.
    - `ocr.models.OCRResult`, `ocr.models.OCRRegion`.
    - `ocr.enums.OCRStatus`.
    - `ocr.exceptions.OCRBackendError`.
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Tuple
import numpy as np

from ocr.enums import OCRStatus
from ocr.models import OCRResult, OCRRegion
from ocr.exceptions import OCRBackendError

logger = logging.getLogger(__name__)


class AbstractOCRBackend(ABC):
    """Abstract base class for pluggable OCR engine backends."""

    @abstractmethod
    def extract_text(self, image: np.ndarray) -> OCRResult:
        """
        Extract text from preprocessed image array into unified OCRResult.

        Args:
            image: Preprocessed 2D/3D numpy image array.

        Returns:
            OCRResult instance containing raw_text, regions, confidence, and status.

        Raises:
            OCRBackendError: If extraction fails or image format is invalid.
        """
        pass

    @abstractmethod
    def get_backend_name(self) -> str:
        """Return human-readable identifier name for backend."""
        pass


class MockOCRBackend(AbstractOCRBackend):
    """Deterministic mock backend for testing without external native binary dependencies."""

    def __init__(
        self,
        mock_text: str = "PARACETAMOL 500mg BATCH-2026-09 EXP 12/2028",
        mock_confidence: float = 0.985,
    ):
        self.mock_text = mock_text
        self.mock_confidence = mock_confidence

    def get_backend_name(self) -> str:
        return "MockOCRBackend"

    def extract_text(self, image: np.ndarray) -> OCRResult:
        if image is None or not isinstance(image, np.ndarray):
            raise OCRBackendError("Invalid image array provided to MockOCRBackend.")

        start_t = time.perf_counter()
        # Create dummy regions for extracted text
        words = self.mock_text.split()
        regions: List[OCRRegion] = []
        for idx, word in enumerate(words):
            x1 = 10 + (idx * 50)
            region = OCRRegion(bbox=(x1, 10, x1 + 40, 30), text=word, confidence=self.mock_confidence)
            regions.append(region)

        elapsed_ms = (time.perf_counter() - start_t) * 1000.0

        return OCRResult(
            raw_text=self.mock_text,
            extracted_regions=tuple(regions),
            identity=None,
            average_confidence=self.mock_confidence,
            processing_time_ms=max(0.1, elapsed_ms),
            status=OCRStatus.VERIFIED if self.mock_confidence >= 0.85 else OCRStatus.UNCERTAIN,
        )


class TesseractBackend(AbstractOCRBackend):
    """PyTesseract wrapper backend implementation."""

    def __init__(self, tesseract_cmd: Optional[str] = None):
        self.tesseract_cmd = tesseract_cmd
        self._available = False
        try:
            import pytesseract
            if self.tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
            self._pytesseract = pytesseract
            self._available = True
        except ImportError:
            logger.warning("pytesseract library not installed. TesseractBackend disabled.")

    def get_backend_name(self) -> str:
        return "TesseractBackend"

    def extract_text(self, image: np.ndarray) -> OCRResult:
        if image is None or not isinstance(image, np.ndarray):
            raise OCRBackendError("Invalid image array provided to TesseractBackend.")

        if not self._available:
            raise OCRBackendError("PyTesseract library is not available in environment.")

        start_t = time.perf_counter()
        try:
            data = self._pytesseract.image_to_data(image, output_type=self._pytesseract.Output.DICT)
            raw_words = []
            regions: List[OCRRegion] = []

            for i in range(len(data["text"])):
                text = data["text"][i].strip()
                conf_val = float(data["conf"][i])
                if text and conf_val > 0:
                    raw_words.append(text)
                    conf_norm = conf_val / 100.0 if conf_val > 1.0 else conf_val
                    x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
                    regions.append(OCRRegion(bbox=(x, y, x + w, y + h), text=text, confidence=conf_norm))

            full_text = " ".join(raw_words)
            avg_conf = float(np.mean([r.confidence for r in regions])) if regions else 0.0
            elapsed_ms = (time.perf_counter() - start_t) * 1000.0

            return OCRResult(
                raw_text=full_text,
                extracted_regions=tuple(regions),
                identity=None,
                average_confidence=avg_conf,
                processing_time_ms=elapsed_ms,
                status=OCRStatus.VERIFIED if avg_conf >= 0.70 else OCRStatus.UNCERTAIN,
            )
        except Exception as err:
            logger.error("Tesseract extraction failed: %s", err)
            raise OCRBackendError(f"Tesseract extraction error: {err}") from err


class EasyOCRBackend(AbstractOCRBackend):
    """EasyOCR backend implementation — pure Python, no external binary required."""

    def __init__(self, languages: Optional[List[str]] = None, gpu: bool = False):
        """
        Initialize EasyOCR backend.

        Args:
            languages: List of language codes (defaults to ['en']).
            gpu: Whether to use GPU acceleration.
        """
        self._languages = languages if languages is not None else ["en"]
        self._gpu = gpu
        self._reader = None
        self._available = False
        try:
            import easyocr
            self._easyocr = easyocr
            self._available = True
        except ImportError:
            logger.warning("easyocr library not installed. EasyOCRBackend disabled.")

    def _get_reader(self):
        """Lazily initialize the EasyOCR Reader (first call downloads models)."""
        if self._reader is None and self._available:
            self._reader = self._easyocr.Reader(self._languages, gpu=self._gpu)
        return self._reader

    def get_backend_name(self) -> str:
        return "EasyOCRBackend"

    def extract_text(self, image: np.ndarray) -> OCRResult:
        if image is None or not isinstance(image, np.ndarray):
            raise OCRBackendError("Invalid image array provided to EasyOCRBackend.")

        if not self._available:
            raise OCRBackendError("easyocr library is not available in environment.")

        reader = self._get_reader()
        if reader is None:
            raise OCRBackendError("Failed to initialize EasyOCR Reader.")

        start_t = time.perf_counter()
        try:
            # EasyOCR returns list of (bbox, text, confidence)
            results = reader.readtext(image)

            raw_words = []
            regions: List[OCRRegion] = []
            for (bbox_pts, text, conf) in results:
                text = text.strip()
                if not text:
                    continue
                raw_words.append(text)
                # bbox_pts is [[x1,y1],[x2,y1],[x2,y2],[x1,y2]] — convert to (x1,y1,x2,y2)
                xs = [pt[0] for pt in bbox_pts]
                ys = [pt[1] for pt in bbox_pts]
                x1, y1, x2, y2 = int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))
                regions.append(OCRRegion(bbox=(x1, y1, x2, y2), text=text, confidence=float(conf)))

            full_text = " ".join(raw_words)
            avg_conf = float(np.mean([r.confidence for r in regions])) if regions else 0.0
            elapsed_ms = (time.perf_counter() - start_t) * 1000.0

            return OCRResult(
                raw_text=full_text,
                extracted_regions=tuple(regions),
                identity=None,
                average_confidence=avg_conf,
                processing_time_ms=elapsed_ms,
                status=OCRStatus.VERIFIED if avg_conf >= 0.70 else OCRStatus.UNCERTAIN,
            )
        except Exception as err:
            logger.error("EasyOCR extraction failed: %s", err)
            raise OCRBackendError(f"EasyOCR extraction error: {err}") from err


__all__ = ["AbstractOCRBackend", "MockOCRBackend", "TesseractBackend", "EasyOCRBackend"]

