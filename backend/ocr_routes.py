"""
Stateless OCR helpers, separate from the vision pipeline (Models A/B/C) and its verification states.

    POST /api/v1/ocr/reverse-side        Stage B of the two-stage inspection: read the printed label on the blister's back.
    POST /api/v1/prescriptions/extract   Read text from an uploaded prescription (image or PDF) for a human to confirm.

Neither route stores the upload or its text, writes to the database, or logs extracted content. Results are
candidates that a person must confirm; they never identify a blister or change a pocket/tablet count.
"""
import re
from typing import Optional

import cv2
import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from backend import warmup
from ocr.backends import shared_easyocr
from ocr.cleaning import OCRTextCleaner
from ocr.parser import OCREntityParser

router = APIRouter(prefix="/api/v1", tags=["OCR"])

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_PRESCRIPTION_BYTES = 8 * 1024 * 1024
MAX_PDF_PAGES = 3
READABLE_CONFIDENCE = 0.70        # same floor the OCR subsystem already uses (OCRManager.min_confidence)
_SESSION_ID = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")
_DOSE = re.compile(r"\b\d+(\.\d+)?\s*(mg|mcg|µg|g|ml|iu)\b|\b(OD|BD|BID|TDS|TID|QID|HS|SOS)\b|\b[01]-[01]-[01](-[01])?\b", re.I)
_HEADERS = {"Cache-Control": "no-store"}


def _ocr_backend():
    """Real OCR only (never the mock, which would invent a medicine). Shares the engine the scan path already loaded."""
    backend = shared_easyocr()
    if not backend._available:
        raise HTTPException(status_code=503, detail="OCR engine (EasyOCR) is not installed on the server.")
    return backend


def _read_limited(file: UploadFile, limit: int) -> bytes:
    data = file.file.read(limit + 1)
    if not data:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(data) > limit:
        raise HTTPException(status_code=413, detail=f"File is larger than {limit // (1024 * 1024)} MB.")
    return data


def _sniff(data: bytes) -> Optional[str]:
    """File type from its first bytes (the filename and declared content-type are not trusted)."""
    if data.startswith(b"\xff\xd8\xff"):
        return "image"
    if data.startswith(b"\x89PNG\r\n\x1a\n") or (data[:4] == b"RIFF" and data[8:12] == b"WEBP"):
        return "image"
    if data.startswith(b"%PDF-"):
        return "pdf"
    return None


def _decode(data: bytes) -> np.ndarray:
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="The file is not a decodable image.")
    return img


def _read_text(img: np.ndarray):
    """Raw OCR (no pre-filtering: on camera-sized images it read printed labels better than the preprocessed path)."""
    try:
        raw = _ocr_backend().extract_text(img)
    except HTTPException:
        raise
    except Exception as err:
        raise HTTPException(status_code=503, detail=f"OCR failed: {type(err).__name__}")
    regions = list(raw.extracted_regions)
    mean_conf = float(np.mean([r.confidence for r in regions])) if regions else 0.0
    # one cleaned line per detected text box (the cleaner alone would collapse every line break)
    lines = [OCRTextCleaner.clean(r.text) for r in regions if r.text.strip()]
    return "\n".join(lines), regions, mean_conf


def _candidates(text: str) -> dict:
    ident = OCREntityParser.parse(text)
    unknown = ("Unknown Medicine", "Unknown Strength", "", None)
    return {
        "medicine_name": None if ident.medicine_name in unknown else ident.medicine_name,
        "strength": None if ident.strength in unknown else ident.strength,
        "batch_number": ident.batch_number,
        "expiry_date": ident.expiry_date,
        "manufacturer": ident.manufacturer,
    }


@router.post("/ocr/reverse-side")
def ocr_reverse_side(
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    scan_no: Optional[int] = Form(None),
):
    if session_id is not None and not _SESSION_ID.match(session_id):
        raise HTTPException(status_code=422, detail="session_id may only contain letters, digits, '_' and '-' (max 64).")
    data = _read_limited(file, MAX_IMAGE_BYTES)
    if _sniff(data) != "image":
        raise HTTPException(status_code=415, detail="Only JPEG, PNG or WEBP images are accepted.")
    warmup.wait()
    text, regions, mean_conf = _read_text(_decode(data))
    status = "NO_TEXT" if not regions else ("READABLE" if mean_conf >= READABLE_CONFIDENCE else "UNCERTAIN")
    return JSONResponse(headers=_HEADERS, content={
        "stage": "B_reverse_label",
        "session_id": session_id,           # echoed so the caller can keep both captures together; not stored here
        "scan_no": scan_no,
        "text": text,
        "regions": [r.to_dict() for r in regions],
        "mean_confidence": round(mean_conf, 4),
        "ocr_status": status,               # NO_TEXT | UNCERTAIN | READABLE (readable still needs a human check)
        "candidates": _candidates(" ".join(text.split())) if text else None,
        "requires_operator_confirmation": True,
        "affects_stage_a_result": False,
        "note": "Reverse-side text only. It does not change pocket counts, tablet counts or verification from the front-side inspection.",
    })


def _pdf_texts(data: bytes):
    try:
        import fitz  # PyMuPDF; installed in the dev environment but not listed in requirements.txt
    except ImportError:
        raise HTTPException(status_code=501, detail="PDF upload needs PyMuPDF on the server (not installed). Upload an image instead.")
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception:
        raise HTTPException(status_code=400, detail="The PDF could not be opened.")
    if doc.needs_pass:
        raise HTTPException(status_code=422, detail="Password-protected PDFs are not supported.")
    texts = []
    for page in list(doc)[:MAX_PDF_PAGES]:
        text = page.get_text("text").strip()
        if len(text) < 10:  # scanned page: no text layer, so read it as an image
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            img = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)
            text = _read_text(cv2.cvtColor(img, cv2.COLOR_RGB2BGR))[0]
        texts.append(text)
    return texts, doc.page_count > MAX_PDF_PAGES


@router.post("/prescriptions/extract")
def extract_prescription(file: UploadFile = File(...)):
    data = _read_limited(file, MAX_PRESCRIPTION_BYTES)
    kind = _sniff(data)
    if kind is None:
        raise HTTPException(status_code=415, detail="Only JPEG, PNG, WEBP or PDF files are accepted.")
    truncated = False
    warmup.wait()
    if kind == "pdf":
        pages, truncated = _pdf_texts(data)
    else:
        pages = [_read_text(_decode(data))[0]]
    text = "\n".join(pages)
    lines = [ln.strip() for ln in re.split(r"[\r\n]+", text) if len(ln.strip()) >= 4]
    candidates = []
    for ln in lines:
        c = _candidates(ln)
        if c["medicine_name"]:
            candidates.append({"line": ln, "medicine_name": c["medicine_name"], "strength": c["strength"]})
    return JSONResponse(headers=_HEADERS, content={
        "status": "NO_TEXT" if not text.strip() else "EXTRACTED",
        "pages_read": len(pages), "pages_truncated": truncated,
        "text": text,
        "candidates": candidates,                                  # only medicines the existing parser recognises
        "dosage_lines": [ln for ln in lines if _DOSE.search(ln)],  # raw lines mentioning a dose/frequency, for the reader
        "requires_human_confirmation": True,
        "identifies_blister": False,
        "note": "Text read from the document, unconfirmed. A prescription never identifies a blister or tablet; that is the vision system's job.",
    })
