"""
Dynamic blister layout: the grid is detected from the image; an expected layout is compared only when
explicitly provided. Grid geometry (pockets) and tablet presence are separate measurements.
"""
import unittest
from unittest.mock import patch

import numpy as np
from fastapi.testclient import TestClient

from app.pipeline import Pipeline
from backend.controllers import InspectionController  # noqa: F401  (imported so patches in the base test class resolve)
from pipeline.inspection_result import InspectionResult, PocketResult
from pipeline.layout import parse_layout
from tests.test_layout import _grid
from tests.test_scan_schedule_workflow import TestScheduledScanWorkflow

IMG = np.tile((np.arange(1300) % 251).astype(np.uint8)[:, None, None], (1, 1300, 3))  # big enough for every test grid


def _pipe(rows, cols, classes=None, boxes=None, expected=None, conf=0.99):
    boxes = boxes if boxes is not None else _grid(rows, cols)
    classes = classes or ["present"] * len(boxes)
    return Pipeline(
        strip_detector=lambda im, conf=None: [im],
        pocket_detector=lambda im, conf=None: np.array(boxes, dtype=float),
        classifier=lambda crops: [(c, conf) for c in classes[:len(crops)]],
        expected_layout=expected,
        min_pocket_conf=0.60,
    )


class TestDetectionWithoutExpectation(unittest.TestCase):
    def test_supported_grid_sizes_are_detected(self):
        for rows, cols in [(2, 5), (5, 3), (3, 4), (1, 6), (4, 4), (7, 2)]:
            with self.subTest(grid=f"{rows}x{cols}"):
                r = _pipe(rows, cols).run(IMG)
                self.assertEqual((r.layout_rows, r.layout_cols, r.total), (rows, cols, rows * cols))
                self.assertIsNone(r.layout_ok)       # nothing was expected, so nothing was compared
                self.assertEqual(r.expected_total, 0)
                self.assertFalse(r.layout_uncertain)
                self.assertEqual(r.verification, "VERIFIED")

    def test_no_fixed_layout_default(self):
        import config
        self.assertIsNone(config.EXPECTED_LAYOUT)


class TestPocketsAreNotTablets(unittest.TestCase):
    def test_15_pockets_all_empty_is_15_missing_not_15_present(self):
        r = _pipe(5, 3, ["missing"] * 15).run(IMG)
        self.assertEqual((r.total, r.present, r.missing), (15, 0, 15))
        self.assertEqual(r.status, "Missing 15 Pill(s)")
        self.assertEqual(r.verification, "VERIFIED")  # geometry is fine; presence is a separate measurement

    def test_15_pockets_10_tablets(self):
        r = _pipe(5, 3, ["present"] * 10 + ["missing"] * 5).run(IMG)
        self.assertEqual((r.total, r.present, r.missing), (15, 10, 5))
        self.assertEqual(len(r.missing_cells), 5)

    def test_low_tablet_confidence_still_requires_review_on_any_grid(self):
        r = _pipe(5, 3, conf=0.5).run(IMG)
        self.assertEqual(r.verification, "REVIEW_REQUIRED")
        self.assertNotIn("Fully Verified", r.status)


class TestExpectedLayoutOnlyWhenProvided(unittest.TestCase):
    def test_wrong_override_is_an_explicit_mismatch(self):
        r = _pipe(5, 3, expected=(2, 5)).run(IMG)
        self.assertEqual(r.verification, "CONFIG_MISMATCH")
        self.assertIn("expected 2x5 (10 pockets), found 5x3 grid with 15 pockets", r.status)

    def test_matching_expectation_is_ok_even_rotated(self):
        self.assertIs(_pipe(5, 3, expected=(3, 5)).run(IMG).layout_ok, True)
        self.assertIs(_pipe(5, 3, expected=(5, 3)).run(IMG).layout_ok, True)

    def test_per_call_expectation_overrides_instance_setting(self):
        r = _pipe(5, 3, expected=(2, 5)).run(IMG, expected_layout=(5, 3))
        self.assertEqual((r.layout_ok, r.verification), (True, "VERIFIED"))


class TestUncertainDetection(unittest.TestCase):
    def test_missing_pocket_box_makes_grid_uncertain_not_invented(self):
        r = _pipe(5, 3, boxes=_grid(5, 3)[:-1]).run(IMG)  # 14 boxes in a 5x3 clustering
        self.assertTrue(r.layout_uncertain)
        self.assertEqual(r.verification, "REVIEW_REQUIRED")
        self.assertIn("grid detection uncertain", r.status)
        self.assertNotIn("Fully Verified", r.status)

    def test_extra_stray_box_makes_grid_uncertain(self):
        boxes = _grid(2, 5) + [(130, 400, 230, 550)]  # a stray detection below the grid
        r = _pipe(2, 5, boxes=boxes).run(IMG)
        self.assertEqual(r.verification, "REVIEW_REQUIRED")

    def test_operator_layout_turns_uncertainty_into_an_explicit_mismatch(self):
        r = _pipe(5, 3, boxes=_grid(5, 3)[:-1], expected=(5, 3)).run(IMG)
        self.assertEqual(r.verification, "CONFIG_MISMATCH")
        self.assertIn("irregular grid", r.status)


class TestParseLayout(unittest.TestCase):
    def test_valid_and_blank(self):
        self.assertEqual(parse_layout("5x3"), (5, 3))
        self.assertEqual(parse_layout(" 5 X 3 "), (5, 3))
        self.assertIsNone(parse_layout(""))
        self.assertIsNone(parse_layout(None))

    def test_invalid(self):
        for bad in ["abc", "5", "5x", "x3", "0x3", "5x0", "50x2", "-1x3", "5x3x2"]:
            with self.subTest(bad), self.assertRaises(ValueError):
                parse_layout(bad)

    def test_env_var_sets_expected_layout_only_when_valid(self):
        import importlib
        import config
        try:
            for value, want in [("5x3", (5, 3)), ("garbage", None), ("", None)]:
                with patch.dict("os.environ", {"EXPECTED_LAYOUT": value}):
                    self.assertEqual(importlib.reload(config).EXPECTED_LAYOUT, want)
        finally:
            importlib.reload(config)


def _result(rows, cols, missing_idx=(), **kw):
    pockets = [PocketResult(i + 1, "missing" if i + 1 in missing_idx else "present", 0.99, (0, 0, 1, 1),
                            row=i // cols + 1, col=i % cols + 1) for i in range(rows * cols)]
    return InspectionResult(total=rows * cols, present=rows * cols - len(missing_idx), missing=len(missing_idx),
                            avg_confidence=0.99, pockets=pockets, layout_rows=rows, layout_cols=cols, **kw)


class _Pipe:
    def __init__(self, *results):
        self.results, self.seen = list(results), []

    def run(self, image, expected_layout=None):
        self.seen.append(expected_layout)
        return self.results.pop(0)


class TestBackendBaselineLayout(unittest.TestCase):
    def setUp(self):
        base = TestScheduledScanWorkflow("test_scan_requires_active_schedule")
        base.setUp()
        self.base, self.db = base, base.db
        self.controller = base._controller()
        self.controller.ocr_mgr.process_image = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("OCR off in test"))
        self.img = np.zeros((20, 20, 3), dtype=np.uint8)

    def _scan(self, pipe, **kw):
        self.controller.pipe = pipe
        return self.controller.inspect_device_session("DEV-TEST-01", image_array=self.img, **kw)

    def test_baseline_stores_detected_layout_and_reports_pockets_separately_from_tablets(self):
        res = self._scan(_Pipe(_result(5, 3, missing_idx=(15,))))
        self.assertTrue(res.success, res.error_message)
        self.assertEqual(res.data["tablet_counts"]["total"], 15)
        self.assertEqual(res.data["tablet_counts"]["present"], 14)
        self.assertEqual((res.data["layout"]["rows"], res.data["layout"]["cols"], res.data["layout"]["pockets"]), (5, 3, 15))
        self.assertEqual(res.data["layout"]["source"], "detected")
        self.assertIsNone(res.data["layout"]["expected"])
        doc = self.db["scan_baselines"].rows[0]
        self.assertEqual((doc["layout_rows"], doc["layout_cols"], doc["layout_source"]), (5, 3, "detected"))

    def test_operator_layout_is_passed_to_the_pipeline_and_stored_as_operator(self):
        pipe = _Pipe(_result(5, 3))
        res = self._scan(pipe, expected_layout=(5, 3))
        self.assertTrue(res.success, res.error_message)
        self.assertEqual(pipe.seen, [(5, 3)])
        self.assertEqual(self.db["scan_baselines"].rows[0]["layout_source"], "operator")

    def test_later_scan_must_match_the_baseline_layout(self):
        self.assertTrue(self._scan(_Pipe(_result(5, 3))).success)
        pipe = _Pipe(_result(5, 3, missing_idx=(15,)))
        res = self._scan(pipe)
        self.assertTrue(res.success, res.error_message)
        self.assertEqual(pipe.seen, [(5, 3)])            # baseline geometry became the expectation
        self.assertEqual(res.data["layout"]["source"], "baseline")

    def test_layout_change_after_baseline_is_rejected_with_rebaseline_hint(self):
        self.assertTrue(self._scan(_Pipe(_result(5, 3))).success)
        changed = _result(2, 5, layout_ok=False, layout_error="expected 5x3 (15 pockets), found 2x5 grid with 10 pockets")
        res = self._scan(_Pipe(changed))
        self.assertFalse(res.success)
        self.assertEqual(res.status_code, 422)
        self.assertIn("CONFIG MISMATCH", res.error_message)
        self.assertIn("new baseline", res.error_message)
        self.assertEqual(res.data["layout"]["rows"], 2)  # UI still gets the detected grid

    def test_uncertain_grid_is_rejected_but_returns_detected_grid_for_confirmation(self):
        res = self._scan(_Pipe(_result(5, 3, layout_uncertain=True)))
        self.assertFalse(res.success)
        self.assertEqual(res.status_code, 422)
        self.assertIn("grid detection uncertain", res.error_message)
        self.assertTrue(res.data["layout"]["uncertain"])
        self.assertEqual(self.db["scan_baselines"].rows, [])  # nothing recorded as a baseline

    def test_invalid_layout_field_is_422_before_any_inspection(self):
        from backend.main import app
        r = TestClient(app).post("/api/v1/devices/DEV-TEST-01/inspection", data={"layout": "abc"})
        self.assertEqual(r.status_code, 422)


# The 16 Model B boxes seen on a live 5x3 capture: 15 real pockets plus a 27 px sliver at the top edge (conf 0.45).
LIVE_16_BOXES = [
    (18, 16, 117, 83), (127, 13, 221, 77), (235, 19, 325, 80), (250, 0, 326, 27),
    (19, 88, 117, 151), (129, 83, 222, 145), (235, 87, 326, 147),
    (19, 160, 116, 222), (126, 160, 222, 223), (235, 159, 326, 219),
    (21, 230, 116, 288), (127, 227, 220, 288), (233, 230, 326, 290),
    (20, 298, 115, 358), (129, 300, 220, 359), (232, 302, 327, 363),
]


class TestFragmentBoxes(unittest.TestCase):
    def test_sliver_box_is_ignored_and_the_5x3_grid_is_clean(self):
        r = _pipe(5, 3, boxes=LIVE_16_BOXES).run(IMG)
        self.assertEqual((r.layout_rows, r.layout_cols, r.total), (5, 3, 15))
        self.assertEqual(r.verification, "VERIFIED")
        self.assertTrue(any("ignored 1 fragment" in line for line in r.execution_report))

    def test_sliver_does_not_block_an_operator_layout_either(self):
        self.assertEqual(_pipe(5, 3, boxes=LIVE_16_BOXES, expected=(5, 3)).run(IMG).verification, "VERIFIED")

    def test_real_pockets_are_never_dropped(self):
        from pipeline.layout import drop_fragments
        self.assertEqual(drop_fragments(_grid(5, 3)), list(range(15)))
        self.assertEqual(drop_fragments(_grid(1, 2)), [0, 1])  # too few boxes to judge size

    def test_missing_pocket_with_only_a_fragment_stays_uncertain(self):
        boxes = _grid(5, 3)[:-1] + [(240, 640, 340, 700)]  # last pocket seen only as a thin sliver
        r = _pipe(5, 3, boxes=boxes).run(IMG)
        self.assertEqual(r.total, 14)
        self.assertEqual(r.verification, "REVIEW_REQUIRED")


class TestReactWiring(unittest.TestCase):
    """Static check only: the UI project has no JS test runner."""

    def test_tabletscan_has_no_layout_box_and_no_invented_pocket_count(self):
        from pathlib import Path
        src = (Path(__file__).resolve().parent.parent / "medidispense-ui" / "src" / "pages" / "TabletIdentification" / "TabletScan.jsx").read_text(encoding="utf-8")
        self.assertNotIn("Blister layout", src)
        self.assertNotIn("/api/v1/vision/layout", src)
        self.assertNotIn("counts.total   ?? 10", src)         # no invented 10-pocket fallback


if __name__ == "__main__":
    unittest.main()
