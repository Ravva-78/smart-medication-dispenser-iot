"""
OCR Verification Subsystem Text Cleaning & Normalization Layer.

Purpose:
    Normalizes raw OCR text strings prior to structured entity parsing.

Responsibilities:
    - Whitespace and line-break collapsing.
    - Unicode normalization (NFKC).
    - OCR confusion matrix correction (e.g. `5OOmg` -> `500mg`, `PARACETAM0L` -> `PARACETAMOL`).
    - Punctuation & artifact cleanup.

Dependencies:
    - Standard library `re`, `unicodedata`.
"""

import re
import unicodedata
from typing import Optional


class OCRTextCleaner:
    """Text normalization utility for cleaning raw OCR noise before entity extraction."""

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """Collapse multiple spaces, tabs, and newlines into single spaces."""
        if not text:
            return ""
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def normalize_unicode(text: str) -> str:
        """Normalize Unicode characters to NFKC standard."""
        if not text:
            return ""
        return unicodedata.normalize("NFKC", text)

    @staticmethod
    def correct_ocr_character_confusion(text: str) -> str:
        """
        Correct common OCR character misclassifications:
        - Letter 'O' / 'o' instead of digit '0' in numbers (e.g., '5OOmg' -> '500mg', '2O28' -> '2028').
        - Digit '0' instead of letter 'O' in uppercase words (e.g., 'PARACETAM0L' -> 'PARACETAMOL').
        """
        if not text:
            return ""

        s = text

        # 1. Correct 'O' / 'o' in dosage strengths: e.g. 5OOmg -> 500mg, 1O0 mg -> 100 mg
        s = re.sub(r"(?<=\d)[O|o]+(?=\s*mg|\s*g|\s*ml|\s*mcg|\b)", lambda m: "0" * len(m.group(0)), s, flags=re.IGNORECASE)
        s = re.sub(r"(\d)[O|o](\d)", r"\g<1>0\g<2>", s)



        # 2. Correct 'O' in 4-digit years: e.g. 2O28 -> 2028, 202O -> 2020
        s = re.sub(r"\b(2)[O|o](\d{2})\b", r"\g<1>0\g<2>", s)
        s = re.sub(r"\b(2\d{2})[O|o]\b", r"\g<1>0", s)


        # 3. Correct '0' in uppercase drug names: e.g. PARACETAM0L -> PARACETAMOL
        def replace_zero_in_word(match):
            word = match.group(0)
            # Only convert '0' to 'O' if the word is predominantly uppercase letters
            if len(word) >= 4 and sum(1 for c in word if c.isupper()) >= len(word) - 2:
                return word.replace("0", "O")
            return word

        s = re.sub(r"\b[A-Z0-9]{4,}\b", replace_zero_in_word, s)

        return s

    @classmethod
    def clean(cls, text: Optional[str]) -> str:
        """
        Execute complete text cleaning pipeline.

        Args:
            text: Raw OCR string or None.

        Returns:
            Normalized, cleaned text string.
        """
        if not text or not isinstance(text, str):
            return ""

        s = cls.normalize_unicode(text)
        s = cls.normalize_whitespace(s)
        s = cls.correct_ocr_character_confusion(s)
        s = cls.normalize_whitespace(s)
        return s


__all__ = ["OCRTextCleaner"]
