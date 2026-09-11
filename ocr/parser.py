"""
OCR Verification Subsystem Medical Entity Parser.

Purpose:
    Extracts structured medical entities (medicine name, dosage strength, form, batch, expiry)
    from cleaned OCR text.

Responsibilities:
    - Match known drug names against internal catalog dictionary.
    - Extract dosage strength patterns (e.g. `500mg`, `250 mg`, `10mg/5ml`).
    - Extract dosage forms (Tablet, Capsule, Syrup, Suspension).
    - Extract manufacturing batch numbers (`BATCH-xxxx`, `BN-xxxx`, `LOT-xxxx`).
    - Extract ISO expiry dates (`EXP MM/YYYY` -> `YYYY-MM-DD`).
    - Construct structured `MedicineIdentity` objects.

Dependencies:
    - Standard library `re`, `typing`.
    - `ocr.cleaning.OCRTextCleaner`.
    - `ocr.models.MedicineIdentity`.
"""

import re
import difflib
from typing import Optional, Tuple, List
from ocr.cleaning import OCRTextCleaner
from ocr.models import MedicineIdentity

# Expanded pharmaceutical drug dictionary for entity matching & fuzzy lookup
KNOWN_MEDICINES = [
    "Paracetamol",
    "Amoxicillin",
    "Ibuprofen",
    "Pantoprazole",
    "Azithromycin",
    "Cetirizine",
    "Metformin",
    "Atorvastatin",
    "Amlodipine",
    "Omeprazole",
    "Levocetirizine",
    "Dolo",
    "Crocin",
    "Aspirin",
    "Ciprofloxacin",
    "Ranitidine",
    "Foracort",
    "Glizid",
    "Brufen",
    "Cyclopam",
    "Dapanorm",
    "Augmentin",
    "Alpenvie",
    "Telmisartan",
    "Losartan",
    "Gliclazide",
    "Vildagliptin",
]

# Aliases and common OCR misread mappings
MEDICINE_ALIASES = {
    "FORACONT": "Foracort",
    "FORACORT G400": "Foracort",
    "GLIZID XR": "Glizid",
    "BRUFEN 400": "Brufen",
    "PCM": "Paracetamol",
    "DOLO 650": "Dolo",
    "AFENME": "Alpenvie",
}

KNOWN_MANUFACTURERS = [
    "PharmaCorp",
    "GlaxoSmithKline",
    "Pfizer",
    "Novartis",
    "Sanofi",
    "Bayer",
    "Cipla",
    "SunPharma",
    "Glenmark",
    "Lupin",
    "Torrent",
    "Alkem",
]


class OCREntityParser:
    """Medical entity parser using regex pattern matching, dictionary lookup, and fuzzy matching."""

    @staticmethod
    def extract_name(text: str) -> Tuple[Optional[str], float]:
        """
        Match known drug name from text string using:
        1. Explicit alias mapping
        2. Exact dictionary substring search
        3. Fuzzy token similarity matching (difflib)
        """
        if not text:
            return None, 0.0

        text_upper = text.upper()

        # 1. Alias lookup
        for alias, canonical_name in MEDICINE_ALIASES.items():
            if alias in text_upper:
                return canonical_name, 0.95

        # 2. Exact substring search
        for med in KNOWN_MEDICINES:
            if med.upper() in text_upper:
                return med, 0.95

        # 3. Token-level fuzzy matching for OCR typos
        tokens = [t.strip(",.!:;()[]{}\"'") for t in text_upper.split() if len(t) >= 4]
        med_upper_list = [m.upper() for m in KNOWN_MEDICINES]

        best_match = None
        best_ratio = 0.0

        for token in tokens:
            # Check close matches for this token
            matches = difflib.get_close_matches(token, med_upper_list, n=1, cutoff=0.72)
            if matches:
                matched_upper = matches[0]
                ratio = difflib.SequenceMatcher(None, token, matched_upper).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    # Find original casing
                    idx = med_upper_list.index(matched_upper)
                    best_match = KNOWN_MEDICINES[idx]

        if best_match and best_ratio >= 0.72:
            return best_match, round(best_ratio * 0.90, 4)

        return None, 0.0

    @staticmethod
    def extract_strength(text: str) -> Tuple[Optional[str], float]:
        """Extract dosage strength (e.g. 500mg, 250 mg, 10mg/5ml)."""
        if not text:
            return None, 0.0

        # Pattern: digits followed optional space, unit mg/5ml, mg/ml, mg, g, mcg, ml (longest first)
        match = re.search(r"\b(\d+(?:\.\d+)?)\s*(mg/5ml|mg/ml|mcg/ml|mg|g|mcg|ml)\b", text, re.IGNORECASE)
        if match:
            digits = match.group(1)
            unit = match.group(2).lower()
            return f"{digits}{unit}", 0.95
        return None, 0.0


    @staticmethod
    def extract_dosage_form(text: str) -> Tuple[str, float]:
        """Extract dosage form (Tablet, Capsule, Syrup, Suspension)."""
        if not text:
            return "Tablet", 0.50

        text_lower = text.lower()
        if "capsule" in text_lower or "cap" in text_lower:
            return "Capsule", 0.95
        if "syrup" in text_lower or "suspension" in text_lower:
            return "Suspension", 0.95
        if "tablet" in text_lower or "tab" in text_lower:
            return "Tablet", 0.95

        return "Tablet", 0.60  # Default fallback

    @staticmethod
    def extract_batch_number(text: str) -> Tuple[Optional[str], float]:
        """Extract manufacturing batch code."""
        if not text:
            return None, 0.0

        match = re.search(r"\b(?:BATCH|LOT|BN|B/N|B\.NO)[:\s\-]*([A-Z0-9\-]{3,15})\b", text, re.IGNORECASE)
        if match:
            code = match.group(1).upper()
            if any(code.startswith(p) for p in ["BATCH-", "LOT-", "BN-"]):
                return code, 0.95
            return f"BATCH-{code}", 0.95
        return None, 0.0


    @staticmethod
    def extract_expiry_date(text: str) -> Tuple[Optional[str], float]:
        """Extract expiry date and normalize to ISO date YYYY-MM-DD or MM/YYYY."""
        if not text:
            return None, 0.0

        # Match EXP MM/YYYY or EXP MM-YYYY or EXP MM/YY
        match_my = re.search(r"\b(?:EXP|EXPIRY|EXP\.DATE)[:\s\-]*(\d{1,2})[/\-](\d{2,4})\b", text, re.IGNORECASE)
        if match_my:
            month = int(match_my.group(1))
            year_val = match_my.group(2)
            year = int(year_val) if len(year_val) == 4 else 2000 + int(year_val)
            return f"{year:04d}-{month:02d}-31", 0.95

        # Match raw MM/YYYY or MM-YYYY without EXP prefix
        match_raw_my = re.search(r"\b(\d{1,2})[/\-](\d{4})\b", text)
        if match_raw_my:
            month = int(match_raw_my.group(1))
            year = int(match_raw_my.group(2))
            if 1 <= month <= 12 and 2020 <= year <= 2040:
                return f"{year:04d}-{month:02d}-31", 0.90

        # Match YYYY-MM-DD
        match_iso = re.search(r"\b(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})\b", text)
        if match_iso:
            return f"{match_iso.group(1)}-{int(match_iso.group(2)):02d}-{int(match_iso.group(3)):02d}", 0.95

        return None, 0.0


    @staticmethod
    def extract_manufacturer(text: str) -> Tuple[Optional[str], float]:
        """Match manufacturer name from dictionary."""
        if not text:
            return None, 0.0

        text_upper = text.upper()
        for mfg in KNOWN_MANUFACTURERS:
            if mfg.upper() in text_upper:
                return mfg, 0.90
        return None, 0.0

    @classmethod
    def parse(cls, raw_text: str) -> MedicineIdentity:
        """
        Parse raw OCR text into structured MedicineIdentity domain model.

        Args:
            raw_text: Raw or pre-cleaned OCR text string.

        Returns:
            Structured MedicineIdentity object.
        """
        cleaned = OCRTextCleaner.clean(raw_text)

        name, n_conf = cls.extract_name(cleaned)
        strength, s_conf = cls.extract_strength(cleaned)
        dosage_form, f_conf = cls.extract_dosage_form(cleaned)
        batch, b_conf = cls.extract_batch_number(cleaned)
        expiry, e_conf = cls.extract_expiry_date(cleaned)
        mfg, m_conf = cls.extract_manufacturer(cleaned)

        conf_scores = [c for c in [n_conf, s_conf, b_conf, e_conf] if c > 0.0]
        avg_confidence = float(sum(conf_scores) / len(conf_scores)) if conf_scores else 0.50

        return MedicineIdentity(
            medicine_name=name if name is not None else "Unknown Medicine",
            strength=strength if strength is not None else "Unknown Strength",
            dosage_form=dosage_form,
            batch_number=batch,
            expiry_date=expiry,
            manufacturer=mfg,
            confidence=avg_confidence,
        )


__all__ = ["OCREntityParser", "KNOWN_MEDICINES", "KNOWN_MANUFACTURERS"]
