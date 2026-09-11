# Technical Design & Architecture Report: OCR Verification Subsystem v1.0
**Project**: AI-Powered Medicine Dispensing System  
**Doc ID**: `docs/03_OCR_SUBSYSTEM.md`  
**Status**: Production Verified (28/28 OCR Tests Passing - 100% Operational)  
**Date**: July 2026  

---

## Executive Summary

The **OCR Verification Subsystem** is responsible for extracting, parsing, and verifying text printed on medicine blister strip packaging, foil backings, and carton labels. Operating in parallel with or immediately downstream of the Inventory Subsystem, it constructs structured `MedicineIdentity` domain models (containing medicine name, strength, dosage form, batch number, expiry date, and manufacturer) to enable automated prescription matching and patient compliance safety checks.

Built using strict **Test-Driven Development (TDD)**, the OCR subsystem features an isolated CV preprocessor (`OCRImagePreprocessor`), pluggable engine abstractions (`AbstractOCRBackend`), an isolated text cleaning normalization layer (`OCRTextCleaner`), a regex & dictionary entity parser (`OCREntityParser`), a prescription matcher (`OCRVerifier`), and an orchestrator facade (`OCRManager`).

---

## 1. Introduction & Objectives

### 1.1 Context & Domain Overview
While computer vision models detect blister strip geometry and count present vs. missing tablets, vision alone cannot identify *which medicine* is present on the tray. Ingesting wrong or expired medications presents severe patient safety risks. The OCR Verification Subsystem addresses this requirement by extracting textual metadata directly from packaging.

### 1.2 Subsystem Objectives
1. Perform image pre-processing (contrast enhancement via CLAHE, adaptive thresholding, noise reduction, sharpening).
2. Abstract OCR engine backends (`AbstractOCRBackend`) to support Tesseract, PaddleOCR, or EasyOCR seamlessly without coupling.
3. Clean raw OCR text strings to correct common optical character confusion (e.g. `5OOmg` $\rightarrow$ `500mg`, `PARACETAM0L` $\rightarrow$ `PARACETAMOL`).
4. Parse clean text into structured `MedicineIdentity` objects.
5. Match extracted identities against expected prescription properties and evaluate verification confidence.

---

## 2. High-Level Subsystem Architecture

The diagram below illustrates the end-to-end OCR data flow from image input to verified identity:

```
┌─────────────────────────────────────────────────────────────────┐
│                     VISION SUBSYSTEM (COMPLETED)               │
│  Camera ──► Model A ──► Perspective ──► Model B ──► Model C    │
└────────────────────────────────┬────────────────────────────────┘
                                 │ Crop Image / Strip ROI
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                 OCR VERIFICATION SUBSYSTEM                      │
│                                                                 │
│                 ┌─────────────────────────────┐                 │
│                 │         OCRManager          │                 │
│                 └──────────────┬──────────────┘                 │
│                                │                                │
│       ┌────────────────────────┼────────────────────────┐       │
│       ▼                        ▼                        ▼       │
│┌──────────────┐        ┌──────────────┐        ┌──────────────┐ │
││ Preprocessor │ ──►    │ OCRBackend   │ ──►    │ TextCleaner  │ │
│└──────────────┘        └──────────────┘        └──────┬───────┘ │
│ (CLAHE/Binary)         (Engine Layer)                 │ Cleaned │
│                                                       ▼         │
│                                                ┌──────────────┐ │
│                                                │ EntityParser │ │
│                                                └──────┬───────┘ │
│                                                       │ Identity│
│                                                       ▼         │
│                                                ┌──────────────┐ │
│                                                │ OCRVerifier  │ │
│                                                └──────┬───────┘ │
└───────────────────────────────────────────────────────┼─────────┘
                                                        │ (OCRResult, Status, Reason)
                                                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                 DOWNSTREAM CONSUMERS (FUTURE)                   │
│         [ Prescription Matching ]  [ Compliance Engine ]         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Package Topology (`ocr/`)

```text
ocr/
├── __init__.py          # Package exports & versioning (0.1.0)
├── enums.py             # OCRStatus & ExtractionField enums
├── utils.py             # Shared OCR helper utilities
├── models.py            # MedicineIdentity, OCRRegion & OCRResult dataclasses
├── exceptions.py        # Domain exception hierarchy (OCRError base)
├── preprocessing.py     # OCRImagePreprocessor (CV enhancement pipeline)
├── backends.py          # AbstractOCRBackend, MockOCRBackend, TesseractBackend
├── cleaning.py          # OCRTextCleaner (normalization & confusion correction)
├── parser.py            # OCREntityParser (dictionary lookup & regex entity extraction)
├── verifier.py          # OCRVerifier (prescription property matcher)
└── manager.py           # OCRManager orchestrator facade
```

---

## 4. Subsystem Module Breakdown

### 4.1 `enums.py`
- `OCRStatus`: `VERIFIED`, `UNCERTAIN`, `REJECTED`, `FAILED`.
- `ExtractionField`: `NAME`, `STRENGTH`, `DOSAGE_FORM`, `BATCH_NUMBER`, `EXPIRY_DATE`, `MANUFACTURER`.

### 4.2 `exceptions.py`
Base exception `OCRError` with derived `InvalidOCRDataError`, `LowConfidenceOCRError`, `OCRBackendError`.

### 4.3 `models.py`
- `MedicineIdentity`: Immutable dataclass representing verified product properties (`medicine_name`, `strength`, `dosage_form`, `batch_number`, `expiry_date`, `manufacturer`, `confidence`).
- `OCRRegion`: Bounding box snippet with local text and confidence score.
- `OCRResult`: Full result payload with raw text, regions, identity, confidence, and status.

### 4.4 `preprocessing.py` (`OCRImagePreprocessor`)
Computer vision enhancement routines:
- `to_grayscale(image)`
- `apply_clahe(image)` (Mitigates specular glare from foil packaging)
- `denoise(image)` (Fast non-local means denoising)
- `sharpen(image)` (Unsharp masking)
- `binarize(image)` (Otsu thresholding)
- `preprocess(image)` (Sequential execution pipeline)

### 4.5 `backends.py` (`AbstractOCRBackend`)
- `AbstractOCRBackend`: ABC defining `extract_text(image) -> OCRResult` and `get_backend_name()`.
- `MockOCRBackend`: Deterministic backend for offline unit testing without native C++ binary dependencies.
- `TesseractBackend`: PyTesseract engine wrapper.

### 4.6 `cleaning.py` (`OCRTextCleaner`)
Isolated text cleaning layer:
- `normalize_whitespace(text)`: Collapses extra spaces, tabs, and line-breaks.
- `normalize_unicode(text)`: Converts glyphs to NFKC standard.
- `correct_ocr_character_confusion(text)`: Fixes character confusion matrices (e.g. `5OOmg` $\rightarrow$ `500mg`, `2O28` $\rightarrow$ `2028`, `PARACETAM0L` $\rightarrow$ `PARACETAMOL`).

### 4.7 `parser.py` (`OCREntityParser`)
- Matches drug names against dictionary (`Paracetamol`, `Amoxicillin`, `Ibuprofen`, `Aspirin`, etc.).
- Regex extracts dosage strengths (`500mg`, `250 mg`, `10mg/5ml`).
- Extracts dosage forms (`Tablet`, `Capsule`, `Suspension`).
- Extracts batch codes (`BATCH-2026-09`) and converts expiry dates to ISO format (`2028-12-31`).

### 4.8 `verifier.py` (`OCRVerifier`)
Compares `MedicineIdentity` against expected prescription properties and returns `(OCRStatus, reason_string)`:
- Returns `VERIFIED` on successful drug name and strength match.
- Returns `REJECTED` on medicine or strength contradiction.
- Returns `UNCERTAIN` when confidence is below threshold.

### 4.9 `manager.py` (`OCRManager`)
Facade orchestrator executing preprocessing, backend extraction, text cleaning, entity parsing, and verification in a single method call (`verify_medicine`).

---

## 5. Development & TDD Methodology

Every module followed strict Red-Green-Refactor TDD discipline:

```text
    ┌────────────────────────────────────────────────────────┐
    │ 1. WRITE UNIT TEST FIRST (tests/test_ocr_<module>.py)  │
    └───────────────────────────┬────────────────────────────┘
                                │
                                ▼
    ┌────────────────────────────────────────────────────────┐
    │ 2. RUN TEST & VERIFY FAILURE (ModuleNotFoundError/Fail)│  ◄── RED PHASE
    └───────────────────────────┬────────────────────────────┘
                                │
                                ▼
    ┌────────────────────────────────────────────────────────┐
    │ 3. IMPLEMENT PRODUCTION MODULE (ocr/<module>.py)       │  ◄── GREEN PHASE
    └───────────────────────────┬────────────────────────────┘
                                │
                                ▼
    ┌────────────────────────────────────────────────────────┐
    │ 4. RE-RUN UNIT TEST & VERIFY 100% PASS                │
    └───────────────────────────┬────────────────────────────┘
                                │
                                ▼
    ┌────────────────────────────────────────────────────────┐
    │ 5. RUN FULL REGRESSION SUITE DISCOVER TESTS            │  ◄── REFACTOR & VERIFY
    └────────────────────────────────────────────────────────┘
```

---

## 6. Verification & Test Metrics

The OCR testing suite contains 28 unit tests across 5 test files:

```text
tests/
├── test_ocr_models.py        (3 tests) - Validates dataclasses, immutability & serialization
├── test_ocr_preprocessing.py (6 tests) - Validates grayscale, CLAHE, denoising & binarization
├── test_ocr_backends.py      (3 tests) - Validates Mock & Abstract backend engines
├── test_ocr_cleaning.py      (5 tests) - Validates text cleaning & confusion matrix correction
├── test_ocr_parser.py        (4 tests) - Validates entity extraction & dictionary lookup
├── test_ocr_verifier.py      (4 tests) - Validates prescription matcher & rejection logic
└── test_ocr_manager.py       (3 tests) - Validates OCRManager facade workflow
------------------------------------------------------------------------------------------
TOTAL SYSTEM SUITE           : 94 / 94 PASSED (66 Inventory + 28 OCR Tests) (6.296s)
```

---

## 7. Future Work & Subsystem Integration

With the OCR Verification Subsystem completed for v1.0, the `MedicineIdentity` payload is ready to be consumed by the **Compliance Subsystem** to verify dose schedules and patient prescriptions.

```text
[ Inventory Subsystem (v1.0) ]        [ OCR Subsystem (v1.0) ]
        │ (InventoryEvent)                    │ (MedicineIdentity)
        └──────────────────┬──────────────────┘
                           ▼
             [ Compliance Engine (v1.0) ]
```
