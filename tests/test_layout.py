"""
Tests for pocket ordering, expected-layout check, truthful stage reports and the
removal of the backend's silent "10 present" fallback.
"""
import random
import unittest

import numpy as np

from app.pipeline import Pipeline
from backend.controllers import InspectionController
from pipeline.inspection_result import InspectionResult
from pipeline.layout import order_boxes, check_layout
from tests.test_scan_schedule_workflow import TestScheduledScanWorkflow


def _grid(rows, cols, w=100, h=150, gap=20):
    return [(c * (w + gap), r * (h + gap), c * (w + gap) + w, r * (h + gap) + h)
            for r in range(rows) for c in range(cols)]


def _pipeline(boxes, classes, expected=(2, 5), perspective=None):
    img = np.tile(np.arange(400, dtype=np.uint8)[:, None, None], (1, 700, 3))  # gradient: flipping changes it
    return Pipeline(
        strip_detector=lambda im, conf=None: [im],
        perspective_fn=perspective,
        pocket_detector=lambda im, conf=None: np.array(boxes, dtype=float),
        classifier=lambda crops: [(c, 0.99) for c in classes],
        expected_layout=expected,
    ), img


class TestOrdering(unittest.TestCase):
    def test_shuffled_boxes_come_back_row_major(self):
        boxes = _grid(2, 5)
        shuffled = boxes[:]
        random.Random(1).shuffle(shuffled)
        order, cells, rows, cols = order_boxes(shuffled)
        self.assertEqual([shuffled[i] for i in order], boxes)
        self.assertEqual((rows, cols), (2, 5))
        self.assertEqual(cells[0], (1, 1))
        self.assertEqual(cells[-1], (2, 5))

    def test_empty(self):
        self.assertEqual(order_boxes([]), ([], [], 0, 0))


class TestCheckLayout(unittest.TestCase):
    def test_ok(self):
        self.assertTrue(check_layout(10, 2, 5, (2, 5))[0])

    def test_rotated_strip_is_ok(self):
        self.assertTrue(check_layout(10, 5, 2, (2, 5))[0])

    def test_missing_pocket_is_mismatch(self):
        ok, msg = check_layout(9, 2, 5, (2, 5))
        self.assertFalse(ok)
        self.assertIn("found 2x5 grid with 9 pockets", msg)

    def test_wrong_grid(self):
        self.assertFalse(check_layout(14, 2, 7, (2, 5))[0])

    def test_disabled(self):
        self.assertTrue(check_layout(3, 1, 3, None)[0])


class TestPipelineLayout(unittest.TestCase):
    def test_full_grid_ok_and_cells_reported(self):
        boxes = _grid(2, 5)
        shuffled = boxes[:]
        random.Random(2).shuffle(shuffled)
        # classifier runs on crops in reading order, so mark the 1st and 6th crops missing
        classes = ["missing" if i in (0, 5) else "present" for i in range(10)]
        pipe, img = _pipeline(shuffled, classes)
        r = pipe.run(img)
        self.assertIs(r.layout_ok, True)
        self.assertEqual((r.total, r.present, r.missing), (10, 8, 2))
        self.assertEqual(r.missing_cells, ["r1c1", "r2c1"])
        self.assertNotIn("CONFIG MISMATCH", r.status)

    def test_nine_pockets_is_config_mismatch(self):
        pipe, img = _pipeline(_grid(2, 5)[:-1], ["present"] * 9)
        r = pipe.run(img)
        self.assertIs(r.layout_ok, False)
        self.assertTrue(r.status.startswith("CONFIG MISMATCH"))
        self.assertTrue(any("CONFIG MISMATCH" in line for line in r.execution_report))

    def test_no_expected_layout_skips_check(self):
        pipe, img = _pipeline(_grid(2, 5)[:-1], ["present"] * 9, expected=None)
        self.assertIsNone(pipe.run(img).layout_ok)

    def test_stage2_report_is_truthful(self):
        boxes = _grid(2, 5)
        pipe, img = _pipeline(boxes, ["present"] * 10, perspective=lambda im: im)
        self.assertTrue(any("not applied" in line for line in pipe.run(img).execution_report))
        pipe, img = _pipeline(boxes, ["present"] * 10, perspective=lambda im: im[::-1].copy())
        self.assertTrue(any("Stage 2" in line and "applied (" in line for line in pipe.run(img).execution_report))


class _FakePipe:
    def __init__(self, result=None, exc=None):
        self.result, self.exc = result, exc

    def run(self, image):
        if self.exc:
            raise self.exc
        return self.result


class TestBackendNoSilentFallback(unittest.TestCase):
    def _scan(self, pipe):
        base = TestScheduledScanWorkflow("test_scan_requires_active_schedule")
        base.setUp()
        controller = base._controller()
        controller.pipe = pipe
        return controller.inspect_device_session("DEV-TEST-01", image_array=np.zeros((20, 20, 3), dtype=np.uint8))

    def test_pipeline_exception_is_an_error(self):
        res = self._scan(_FakePipe(exc=RuntimeError("model missing")))
        self.assertFalse(res.success)
        self.assertEqual(res.status_code, 500)

    def test_zero_pockets_is_an_error(self):
        res = self._scan(_FakePipe(InspectionResult()))
        self.assertFalse(res.success)
        self.assertEqual(res.status_code, 422)

    def test_config_mismatch_is_an_error(self):
        bad = InspectionResult(total=9, present=9, layout_ok=False, layout_error="expected 2x5 (10 pockets), found 2x5 grid with 9 pockets")
        res = self._scan(_FakePipe(bad))
        self.assertFalse(res.success)
        self.assertEqual(res.status_code, 422)
        self.assertIn("CONFIG MISMATCH", res.error_message)


if __name__ == "__main__":
    unittest.main()
