"""
Isolated audit-phase additions: synthetic TEST catalogue, real-sample intake tool, reverse-side OCR (Stage B)
and prescription text extraction. OCR is faked: these tests prove validation, separation from the vision
result and no-fabrication behaviour, not OCR accuracy.
"""
import csv
import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend import ocr_routes
from backend.test_catalogue_routes import CATALOGUE_PATH, router as catalogue_router
from ocr.models import OCRRegion

ROOT = Path(__file__).resolve().parent.parent
PNG = cv2.imencode(".png", np.tile((np.arange(120) * 2).astype(np.uint8)[:, None, None], (1, 200, 3)))[1].tobytes()


def _load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeOCR:
    """Stands in for EasyOCRBackend: returns the given (text, confidence) regions."""
    _available = True

    def __init__(self, *regions):
        self.regions = [OCRRegion((0, 0, 10, 10), t, c) for t, c in regions]

    def extract_text(self, img):
        return types.SimpleNamespace(raw_text=" ".join(r.text for r in self.regions), extracted_regions=tuple(self.regions))


def _client():
    app = FastAPI()
    app.include_router(ocr_routes.router)
    app.include_router(catalogue_router)
    return TestClient(app)


class TestSyntheticCatalogue(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(CATALOGUE_PATH.read_text(encoding="utf-8"))

    def test_everything_is_labelled_test_data(self):
        self.assertIn("SYNTHETIC TEST DATA", self.data["banner"])
        self.assertEqual(self.data["data_status"], "TEST DATA")
        self.assertFalse(self.data["has_real_photos"])
        self.assertGreaterEqual(len(self.data["entries"]), 10)
        for e in self.data["entries"]:
            self.assertEqual(e["data_status"], "TEST DATA", e["test_id"])
            self.assertIn("fictional", e["fictional_schedule"]["label"].lower())
            self.assertTrue("placeholder" in e["label_strength_example"].lower(), e["test_id"])

    def test_no_photos_or_patient_advice_fields(self):
        for e in self.data["entries"]:
            self.assertFalse({"image", "photo", "image_url", "dose_advice", "patient_id"} & set(e), e["test_id"])

    def test_ids_are_unique_and_prefixed(self):
        ids = [e["test_id"] for e in self.data["entries"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(i.startswith("TEST-") for i in ids))

    def test_endpoint_serves_the_same_content(self):
        r = _client().get("/api/v1/test-catalogue")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), self.data)


class TestRealSampleIntake(unittest.TestCase):
    def setUp(self):
        self.mod = _load_script("add_real_sample")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "real_samples"
        self.img = Path(self.tmp.name) / "photo.png"
        self.img.write_bytes(PNG)

    def _rows(self):
        with (self.root / "samples.csv").open(newline="", encoding="utf-8") as fh:
            return list(csv.DictReader(fh))

    def test_unknown_medicine_is_recorded_as_unknown(self):
        row = self.mod.add_sample(self.img, root=self.root)
        self.assertEqual((row["label"], row["label_source"]), ("UNKNOWN", "unknown"))
        self.assertTrue((self.root / row["file"]).is_file())

    def test_operator_supplied_name_is_kept_with_its_source(self):
        row = self.mod.add_sample(self.img, label=" Dolo 650 ", root=self.root)
        self.assertEqual((row["label"], row["label_source"]), ("Dolo 650", "operator"))
        row2 = self.mod.add_sample(self.img, label="Paracetamol", source="packaging", root=self.root)
        self.assertEqual(row2["label_source"], "packaging")
        self.assertEqual(len(self._rows()), 2)

    def test_invalid_combinations_and_files_are_rejected(self):
        with self.assertRaises(ValueError):
            self.mod.add_sample(self.img, label="X", source="unknown", root=self.root)   # a name must say who supplied it
        with self.assertRaises(ValueError):
            self.mod.add_sample(self.img, source="operator", root=self.root)             # a source without a name
        with self.assertRaises(ValueError):
            self.mod.add_sample(Path(self.tmp.name) / "missing.png", root=self.root)
        bad = Path(self.tmp.name) / "not_image.png"
        bad.write_bytes(b"hello")
        with self.assertRaises(ValueError):
            self.mod.add_sample(bad, root=self.root)
        self.assertFalse((self.root / "samples.csv").exists())                           # nothing recorded on failure

    def test_original_is_copied_not_moved_and_ids_never_collide(self):
        a = self.mod.add_sample(self.img, root=self.root)
        b = self.mod.add_sample(self.img, root=self.root)
        self.assertTrue(self.img.is_file())
        self.assertNotEqual(a["sample_id"], b["sample_id"])
        header = (self.root / "samples.csv").read_text(encoding="utf-8").splitlines()[0]
        self.assertEqual(header.count("sample_id"), 1)                                   # header written once


class TestReverseSideOCR(unittest.TestCase):
    def setUp(self):
        self.client = _client()

    def _post(self, fake, content=PNG, **data):
        with patch.object(ocr_routes, "_ocr_backend", return_value=fake):
            return self.client.post("/api/v1/ocr/reverse-side", files={"file": ("back.png", content, "image/png")}, data=data)

    def test_readable_label_returns_text_confidence_and_requires_confirmation(self):
        r = self._post(FakeOCR(("PREDNISOLONE 10mg TABLETS", 0.85), ("LOT 040523 EXP 10/26", 0.80)), session_id="sess_abc", scan_no="1")
        self.assertEqual(r.status_code, 200)
        j = r.json()
        self.assertEqual((j["stage"], j["ocr_status"], j["session_id"], j["scan_no"]), ("B_reverse_label", "READABLE", "sess_abc", 1))
        self.assertAlmostEqual(j["mean_confidence"], 0.825, places=3)
        self.assertTrue(j["requires_operator_confirmation"])
        self.assertFalse(j["affects_stage_a_result"])
        self.assertEqual(len(j["regions"]), 2)

    def test_response_carries_no_vision_or_verification_fields(self):
        j = self._post(FakeOCR(("PARACETAMOL 500mg", 0.9))).json()
        for forbidden in ("tablet_counts", "verification", "present", "missing", "total", "layout", "status"):
            self.assertNotIn(forbidden, j)

    def test_low_confidence_is_uncertain_and_no_text_is_no_text(self):
        self.assertEqual(self._post(FakeOCR(("P4R4CE7AM0L", 0.40))).json()["ocr_status"], "UNCERTAIN")
        j = self._post(FakeOCR()).json()
        self.assertEqual((j["ocr_status"], j["candidates"], j["text"]), ("NO_TEXT", None, ""))

    def test_unknown_text_never_becomes_a_medicine_name(self):
        j = self._post(FakeOCR(("XQZ LMNOP 123", 0.9))).json()
        self.assertIsNone(j["candidates"]["medicine_name"])
        self.assertIsNone(j["candidates"]["strength"])

    def test_input_validation(self):
        self.assertEqual(self._post(FakeOCR(("A", 0.9)), content=b"").status_code, 400)
        self.assertEqual(self._post(FakeOCR(("A", 0.9)), content=b"GIF89a....").status_code, 415)
        self.assertEqual(self._post(FakeOCR(("A", 0.9)), content=b"%PDF-1.4 x").status_code, 415)        # PDFs are not label photos
        self.assertEqual(self._post(FakeOCR(("A", 0.9)), content=b"\x89PNG\r\n\x1a\n" + b"junk").status_code, 400)
        self.assertEqual(self._post(FakeOCR(("A", 0.9)), session_id="bad id!").status_code, 422)
        with patch.object(ocr_routes, "MAX_IMAGE_BYTES", 100):
            self.assertEqual(self._post(FakeOCR(("A", 0.9))).status_code, 413)

    def test_missing_ocr_engine_is_503_not_a_mock_result(self):
        class Gone:
            _available = False
        with patch.object(ocr_routes, "shared_easyocr", return_value=Gone()):
            r = self.client.post("/api/v1/ocr/reverse-side", files={"file": ("b.png", PNG, "image/png")})
        self.assertEqual(r.status_code, 503)

    def test_ocr_engine_crash_is_503_without_leaking_details(self):
        class Boom(FakeOCR):
            def extract_text(self, img):
                raise RuntimeError("secret path C:/x")
        r = self._post(Boom())
        self.assertEqual(r.status_code, 503)
        self.assertNotIn("secret", r.text)

    def test_responses_are_not_cacheable(self):
        self.assertEqual(self._post(FakeOCR(("A", 0.9))).headers["cache-control"], "no-store")


class TestPrescriptionExtract(unittest.TestCase):
    def setUp(self):
        self.client = _client()

    def _post(self, fake, content=PNG, name="rx.png"):
        with patch.object(ocr_routes, "_ocr_backend", return_value=fake):
            return self.client.post("/api/v1/prescriptions/extract", files={"file": (name, content, "application/octet-stream")})

    def test_image_returns_candidates_and_dose_lines_as_unconfirmed(self):
        fake = FakeOCR(("Paracetamol 500mg BD", 0.9), ("Amoxicillin 250 mg TDS", 0.9), ("Dr A Kumar Reg 1234", 0.9))
        j = self._post(fake).json()
        names = [c["medicine_name"] for c in j["candidates"]]
        self.assertEqual(names, ["Paracetamol", "Amoxicillin"])
        self.assertEqual(len(j["dosage_lines"]), 2)
        self.assertTrue(j["requires_human_confirmation"])
        self.assertFalse(j["identifies_blister"])

    def test_unrecognised_text_gives_no_invented_medicine(self):
        fake = FakeOCR(("Dr A Kumar", 0.9))
        j = self._post(fake).json()
        self.assertEqual(j["candidates"], [])
        self.assertEqual(self._post(FakeOCR()).json()["status"], "NO_TEXT")

    def test_file_validation(self):
        self.assertEqual(self._post(FakeOCR(), content=b"").status_code, 400)
        self.assertEqual(self._post(FakeOCR(), content=b"MZ\x90\x00 exe", name="rx.pdf").status_code, 415)   # name says pdf, bytes say exe
        self.assertEqual(self._post(FakeOCR(), content=b"PK\x03\x04 zip").status_code, 415)
        self.assertEqual(self._post(FakeOCR(), content=b"\x89PNG\r\n\x1a\n" + b"junk").status_code, 400)
        with patch.object(ocr_routes, "MAX_PRESCRIPTION_BYTES", 100):
            self.assertEqual(self._post(FakeOCR()).status_code, 413)

    @unittest.skipUnless(importlib.util.find_spec("fitz"), "PyMuPDF not installed")
    def test_pdf_text_layer_is_read_without_ocr(self):
        import fitz
        doc = fitz.open()
        doc.new_page().insert_text((72, 100), "Tab Paracetamol 500mg BD for 5 days")
        pdf = doc.tobytes()
        j = self._post(FakeOCR(("SHOULD NOT BE USED", 0.9)), content=pdf, name="rx.pdf").json()
        self.assertEqual(j["pages_read"], 1)
        self.assertEqual([c["medicine_name"] for c in j["candidates"]], ["Paracetamol"])
        self.assertNotIn("SHOULD NOT BE USED", j["text"])

    @unittest.skipUnless(importlib.util.find_spec("fitz"), "PyMuPDF not installed")
    def test_scanned_pdf_falls_back_to_ocr_and_corrupt_pdf_is_400(self):
        import fitz
        doc = fitz.open()
        doc.new_page()
        j = self._post(FakeOCR(("Ibuprofen 400mg", 0.9)), content=doc.tobytes(), name="scan.pdf").json()
        self.assertEqual([c["medicine_name"] for c in j["candidates"]], ["Ibuprofen"])
        self.assertEqual(self._post(FakeOCR(), content=b"%PDF-1.4 garbage", name="x.pdf").status_code, 400)

    def test_pdf_without_pymupdf_is_501_not_a_fake_result(self):
        with patch.dict(sys.modules, {"fitz": None}):
            r = self._post(FakeOCR(), content=b"%PDF-1.4 x", name="x.pdf")
        self.assertEqual(r.status_code, 501)

    def test_no_database_is_touched(self):
        src = (ROOT / "backend" / "ocr_routes.py").read_text(encoding="utf-8")
        self.assertNotIn("import database", src)
        self.assertNotIn("from database", src)
        self.assertNotIn("logger.", src)  # extracted content must not be logged


if __name__ == "__main__":
    unittest.main()
