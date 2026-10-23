"""
Verification-status tests: an uncertain, failed or incomplete inspection must never read
"Inventory Fully Verified", and the known white-strip failure must not be reported as verified.
"""
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from app.pipeline import Pipeline
from config import MODEL_A_PATH, MODEL_B_PATH, MODEL_C_PATH, MIN_POCKET_CONF
from pipeline.inspection_result import InspectionResult, PocketResult
from tests.test_layout import _grid

ROOT = Path(__file__).resolve().parent.parent
IMG = np.tile(np.arange(400, dtype=np.uint8)[:, None, None], (1, 700, 3))


def _pipe(classes, confs=None, boxes=None, classifier=True, expected=(2, 5), min_conf=MIN_POCKET_CONF):
    confs = confs or [0.99] * len(classes)
    return Pipeline(
        strip_detector=lambda im, conf=None: [im],
        pocket_detector=lambda im, conf=None: np.array(boxes if boxes is not None else _grid(2, 5), dtype=float),
        classifier=(lambda crops: list(zip(classes, confs))) if classifier else None,
        expected_layout=expected,
        min_pocket_conf=min_conf,
    )


class TestVerificationStatus(unittest.TestCase):
    def test_confident_full_grid_is_verified(self):
        r = _pipe(["present"] * 10).run(IMG)
        self.assertEqual(r.verification, "VERIFIED")
        self.assertEqual(r.status, "Inventory Fully Verified")

    def test_low_confidence_pocket_is_review_required_not_verified(self):
        # numbers taken from the white-strip run: empty pocket called "present" at 0.556
        confs = [0.99] * 10
        confs[5] = 0.556
        r = _pipe(["present"] * 10, confs).run(IMG)
        self.assertEqual(r.verification, "REVIEW_REQUIRED")
        self.assertEqual(r.uncertain_cells, ["r2c1"])
        self.assertNotIn("Fully Verified", r.status)
        self.assertEqual((r.total, r.present, r.missing), (10, 10, 0))  # counts reported, but not trusted

    def test_confidence_check_can_be_disabled(self):
        confs = [0.99] * 9 + [0.1]
        self.assertEqual(_pipe(["present"] * 10, confs, min_conf=None).run(IMG).verification, "VERIFIED")

    def test_missing_tablets_with_confidence_is_verified_but_not_fully_verified(self):
        r = _pipe(["missing", "missing"] + ["present"] * 8).run(IMG)
        self.assertEqual(r.verification, "VERIFIED")
        self.assertEqual(r.status, "Missing 2 Pill(s)")

    def test_layout_mismatch_is_not_verified(self):
        r = _pipe(["present"] * 9, boxes=_grid(2, 5)[:-1]).run(IMG)
        self.assertEqual(r.verification, "CONFIG_MISMATCH")
        self.assertNotIn("Fully Verified", r.status)

    def test_classifier_not_loaded_is_failed(self):
        r = _pipe([], classifier=False).run(IMG)
        self.assertEqual(r.verification, "FAILED")
        self.assertIn("Model C", r.status)
        self.assertNotIn("Fully Verified", r.status)

    def test_unreadable_image_path_is_failed(self):
        r = _pipe(["present"] * 10).run(ROOT / "does_not_exist.png")
        self.assertEqual(r.verification, "FAILED")
        self.assertIn("could not read image", r.error)

    def test_empty_array_is_failed(self):
        r = _pipe(["present"] * 10).run(np.zeros((0, 0, 3), dtype=np.uint8))
        self.assertEqual(r.verification, "FAILED")

    def test_no_pockets_is_not_verified(self):
        r = _pipe([], boxes=[]).run(IMG)
        self.assertEqual(r.verification, "NO_POCKETS")
        self.assertNotIn("Fully Verified", r.status)

    def test_fully_verified_text_only_when_verified(self):
        cases = [
            InspectionResult(total=10, present=10, pockets=[PocketResult(1, "present", 0.2, (0, 0, 1, 1))], uncertain_cells=["r1c1"]),
            InspectionResult(total=10, present=10, layout_ok=False, layout_error="x"),
            InspectionResult(total=10, present=10, error="boom"),
            InspectionResult(),
        ]
        for r in cases:
            self.assertNotEqual(r.verification, "VERIFIED")
            self.assertNotIn("Fully Verified", r.status)

    def test_to_dict_separates_expected_detected_and_verification(self):
        d = _pipe(["present"] * 10).run(IMG).to_dict()
        for key in ("expected_total", "total", "present", "missing", "min_confidence", "uncertain_cells", "verification", "error"):
            self.assertIn(key, d)
        self.assertEqual(d["expected_total"], 10)


@unittest.skipUnless(all(p.exists() for p in (MODEL_A_PATH, MODEL_B_PATH, MODEL_C_PATH)), "production models not present")
class TestWhiteStripRegression(unittest.TestCase):
    """Real models on the known failure. Asserts status honesty only; classification accuracy is tracked by scripts/eval_counts.py."""

    def test_white_strip_is_not_called_fully_verified(self):
        r = Pipeline.from_defaults().run(ROOT / "qa_testing" / "test_images" / "two eaten.png")
        truth_correct = (r.total, r.present, r.missing) == (10, 8, 2)
        if not truth_correct:
            self.assertNotEqual(r.verification, "VERIFIED")
            self.assertNotIn("Fully Verified", r.status)


class TestInputCompatibility(unittest.TestCase):
    def test_array_and_file_path_give_same_result(self):
        pipe = _pipe(["present"] * 10)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "strip.png"
            cv2.imwrite(str(path), IMG)
            self.assertEqual(pipe.run(IMG).to_dict(), pipe.run(path).to_dict())


if __name__ == "__main__":
    unittest.main()
