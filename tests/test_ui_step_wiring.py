"""
Static guard-rails for the reverse-side panel and prescription upload dialog. The UI project has no JS test
runner, so these read the source: they check separation from Stage A, no persistence and the confirm/reject
requirements. They do not prove the browser behaviour (that needs the manual test).
"""
import re
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "medidispense-ui" / "src"


def _read(rel):
    return (SRC / rel).read_text(encoding="utf-8")


class TestReverseSidePanel(unittest.TestCase):
    def setUp(self):
        self.panel = _read("pages/TabletIdentification/ReverseSidePanel.jsx")
        self.scan = _read("pages/TabletIdentification/TabletScan.jsx")

    def test_scan_page_hook_is_read_only_and_only_after_a_front_side_result(self):
        calls = re.findall(r"<ReverseSidePanel[^>]*/>", self.scan)
        self.assertEqual(len(calls), 1)
        self.assertIn("{result && <ReverseSidePanel", self.scan)
        # only plain values are passed: no setters or refs that could change Stage A state
        self.assertEqual(sorted(re.findall(r"(\w+)=\{", calls[0])), ["apiUrl", "scanNo", "sessionId"])
        self.assertEqual(self.scan.count("ReverseSidePanel"), 3)  # import (name + path) + one use

    def test_panel_cannot_touch_stage_a_or_persist_anything(self):
        for forbidden in ("setResult", "setHistory", "setImgFile", "setPreview", "apiClient", "localStorage",
                          "sessionStorage", "indexedDB", "/inspection", "tablet_counts"):
            self.assertNotIn(forbidden, self.panel, forbidden)
        self.assertEqual(re.findall(r'method: "(\w+)"', self.panel), ["POST"])
        self.assertIn("/api/v1/ocr/reverse-side", self.panel)
        self.assertEqual(self.panel.count("fetch("), 1)  # only the OCR route; camera frames go through the shared queue
        self.assertIn("fetchCameraFrame(apiUrl, { signal, exclusive: true })", self.panel)
        self.assertIn("beginExclusive()", self.panel)
        self.assertIn("endExclusive()", self.panel)

    def test_explicit_confirm_reject_uncertainty_and_orientation_prompts(self):
        for text in ("Confirm", "Reject", "unconfirmed", "mean confidence", "Turn the blister over", "Turn the blister back",
                     "not saved", "never changes the front-side"):
            self.assertIn(text, self.panel, text)
        self.assertIn("NO_TEXT", self.panel)  # confirm is disabled when nothing was read


class TestPrescriptionUpload(unittest.TestCase):
    def setUp(self):
        self.modal = _read("components/PrescriptionUploadModal.jsx")
        self.page = _read("pages/Prescriptions.jsx")

    def test_dialog_never_saves(self):
        for forbidden in ("apiClient", "localStorage", "sessionStorage", "indexedDB", "/prescriptions\"", "/patients"):
            self.assertNotIn(forbidden, self.modal, forbidden)
        self.assertEqual(self.modal.count("fetch("), 1)
        self.assertIn("/api/v1/prescriptions/extract", self.modal)

    def test_unconfirmed_until_the_operator_checks_the_details(self):
        self.assertIn("Unconfirmed.", self.modal)
        self.assertIn("does not identify any blister", self.modal)
        self.assertIn("const canContinue = fields.medication.trim() && checked;", self.modal)
        self.assertIn("disabled={!canContinue}", self.modal)

    def test_extracted_values_are_not_prefilled_with_defaults(self):
        self.assertIn('useState({ medication: "", dosage: "", frequency: "", doctor: "" })', self.modal)

    def test_page_still_has_exactly_one_save_path_and_it_is_the_existing_one(self):
        self.assertEqual(self.page.count('apiClient.post("/prescriptions"'), 1)
        self.assertIn("initialValues={draft}", self.page)
        self.assertIn("setDraft(values); setUploading(false); setAdding(true);", self.page)  # hands over to the existing form


if __name__ == "__main__":
    unittest.main()
