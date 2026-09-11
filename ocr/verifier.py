"""
OCR Verification Subsystem Prescription Matching Engine.

Purpose:
    Compares extracted MedicineIdentity objects against expected prescription specifications.

Responsibilities:
    - Assert medicine name equivalence.
    - Assert dosage strength equivalence.
    - Evaluate overall extraction confidence against minimum threshold.
    - Return `(OCRStatus, reason_string)` tuple.

Dependencies:
    - `ocr.models.MedicineIdentity`.
    - `ocr.enums.OCRStatus`.
"""

import logging
from typing import Tuple, Optional
from ocr.models import MedicineIdentity
from ocr.enums import OCRStatus

logger = logging.getLogger(__name__)


class OCRVerifier:
    """Verification engine comparing extracted OCR MedicineIdentity against expected prescription rules."""

    @staticmethod
    def verify(
        extracted: MedicineIdentity,
        expected_name: str,
        expected_strength: Optional[str] = None,
        min_confidence: float = 0.70,
    ) -> Tuple[OCRStatus, str]:
        """
        Verify an extracted MedicineIdentity against expected prescription properties.

        Args:
            extracted: MedicineIdentity extracted by OCR parser.
            expected_name: Expected medicine product name.
            expected_strength: Optional expected strength (e.g., '500mg').
            min_confidence: Minimum required confidence threshold.

        Returns:
            Tuple of (OCRStatus, detailed_reason_string).
        """
        logger.debug("Verifying extracted identity '%s' against expected '%s'", extracted.medicine_name, expected_name)

        # 1. Low confidence check
        if extracted.confidence < min_confidence:
            reason = f"Low confidence (score={extracted.confidence:.4f} < threshold={min_confidence:.2f})"
            logger.warning("OCR verification uncertain: %s", reason)
            return OCRStatus.UNCERTAIN, reason

        # 2. Medicine name check
        if extracted.medicine_name.strip().lower() != expected_name.strip().lower():
            reason = f"Medicine mismatch: extracted '{extracted.medicine_name}' != expected '{expected_name}'"
            logger.warning("OCR verification rejected: %s", reason)
            return OCRStatus.REJECTED, reason

        # 3. Dosage strength check (if expected_strength provided)
        if expected_strength is not None:
            norm_extracted_str = extracted.strength.strip().lower().replace(" ", "")
            norm_expected_str = expected_strength.strip().lower().replace(" ", "")
            if norm_extracted_str != norm_expected_str:
                reason = f"Strength mismatch: extracted '{extracted.strength}' != expected '{expected_strength}'"
                logger.warning("OCR verification rejected: %s", reason)
                return OCRStatus.REJECTED, reason

        reason = f"Match successful for '{expected_name}' ({extracted.strength})"
        logger.info("OCR verification passed: %s", reason)
        return OCRStatus.VERIFIED, reason


__all__ = ["OCRVerifier"]
