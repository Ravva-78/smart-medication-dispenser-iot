"""
Software speed-ups: OCR GPU flag (with CPU fallback), shared OCR engine, start-up warm-up, config flags and the
React wiring for single-flight camera access. Nothing here touches models, thresholds or verification states.
"""
import importlib
import threading
import time
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from backend import warmup
from ocr import backends
from ocr.backends import EasyOCRBackend, shared_easyocr

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "medidispense-ui" / "src" / "pages" / "TabletIdentification"


class FakeEasy:
    """Stands in for the easyocr module: records the gpu flag each Reader was built with."""
    def __init__(self, fail_on_gpu=False, fail_always=False):
        self.built, self.fail_on_gpu, self.fail_always = [], fail_on_gpu, fail_always

    def Reader(self, languages, gpu):
        self.built.append(gpu)
        if self.fail_always or (gpu and self.fail_on_gpu):
            raise RuntimeError("CUDA out of memory")
        return object()


def _backend(fake, **kw):
    b = EasyOCRBackend(**kw)
    b._easyocr, b._available = fake, True
    return b


class TestOcrGpuFlag(unittest.TestCase):
    def _reader_gpu(self, flag, cuda, **kw):
        fake = FakeEasy()
        with patch("config.OCR_USE_GPU", flag), patch("torch.cuda.is_available", return_value=cuda):
            _backend(fake, **kw)._get_reader()
        return fake.built

    def test_default_uses_gpu_only_when_flag_on_and_cuda_available(self):
        self.assertEqual(self._reader_gpu(True, True), [True])
        self.assertEqual(self._reader_gpu(False, True), [False])
        self.assertEqual(self._reader_gpu(True, False), [False])

    def test_explicit_argument_wins_over_the_flag(self):
        self.assertEqual(self._reader_gpu(True, True, gpu=False), [False])
        self.assertEqual(self._reader_gpu(False, False, gpu=True), [True])

    def test_gpu_init_failure_falls_back_to_cpu(self):
        fake = FakeEasy(fail_on_gpu=True)
        with patch("config.OCR_USE_GPU", True), patch("torch.cuda.is_available", return_value=True):
            reader = _backend(fake)._get_reader()
        self.assertIsNotNone(reader)
        self.assertEqual(fake.built, [True, False])

    def test_cpu_failure_is_not_swallowed(self):
        fake = FakeEasy(fail_always=True)
        with patch("config.OCR_USE_GPU", False), self.assertRaises(RuntimeError):
            _backend(fake)._get_reader()
        self.assertEqual(fake.built, [False])

    def test_one_shared_engine_per_process(self):
        with patch.object(backends, "_shared_easyocr", None):
            a, b = shared_easyocr(), shared_easyocr()
        self.assertIs(a, b)

    def test_ocr_manager_and_ocr_routes_use_the_shared_engine(self):
        from backend import ocr_routes
        from ocr.manager import OCRManager
        engine = types.SimpleNamespace(_available=True)
        with patch("ocr.manager.shared_easyocr", return_value=engine), patch.object(ocr_routes, "shared_easyocr", return_value=engine):
            self.assertIs(OCRManager().backend, engine)
            self.assertIs(ocr_routes._ocr_backend(), engine)


class TestConfigFlags(unittest.TestCase):
    def _config(self, **env):
        import config
        with patch.dict("os.environ", env):
            return importlib.reload(config)

    def tearDown(self):
        import config
        importlib.reload(config)

    def test_defaults(self):
        c = self._config()
        self.assertEqual((c.CAMERA_RETRIES, c.CAMERA_DEADLINE_S, c.OCR_USE_GPU, c.WARMUP_ON_START), (2, 45.0, True, True))

    def test_each_feature_can_be_switched_off(self):
        c = self._config(CAMERA_RETRIES="0", OCR_USE_GPU="0", WARMUP_ON_START="0")
        self.assertEqual((c.CAMERA_RETRIES, c.OCR_USE_GPU, c.WARMUP_ON_START), (0, False, False))

    def test_garbage_values_fall_back_to_defaults(self):
        c = self._config(CAMERA_RETRIES="lots", CAMERA_DEADLINE_S="soon")
        self.assertEqual((c.CAMERA_RETRIES, c.CAMERA_DEADLINE_S), (2, 45.0))


class TestWarmup(unittest.TestCase):
    def _service(self):
        calls = []
        pipe = types.SimpleNamespace(
            strip_detector=lambda img: calls.append("A"), pocket_detector=lambda img: calls.append("B"),
            classifier=lambda crops: calls.append("C"))
        ocr = MagicMock()
        ocr._get_reader.side_effect = lambda: calls.append("ocr-init")
        ocr.extract_text.side_effect = lambda img: calls.append("ocr-run")
        controller = types.SimpleNamespace(pipe=pipe, ocr_mgr=types.SimpleNamespace(backend=ocr))
        return types.SimpleNamespace(inspection_controller=controller), calls

    def test_warms_every_stage_with_a_blank_frame_and_releases_waiters(self):
        svc, calls = self._service()
        warmup.run(lambda: svc)
        self.assertEqual(calls, ["A", "B", "C", "ocr-init", "ocr-run"])
        self.assertTrue(warmup._idle.is_set())

    def test_failure_never_raises_and_never_leaves_requests_waiting(self):
        def boom():
            raise RuntimeError("no GPU")
        warmup.run(boom)
        self.assertTrue(warmup._idle.is_set())

    def test_mock_ocr_backend_is_skipped(self):
        svc, calls = self._service()
        svc.inspection_controller.ocr_mgr.backend = types.SimpleNamespace()   # e.g. no _get_reader
        warmup.run(lambda: svc)
        self.assertEqual(calls, ["A", "B", "C"])

    def test_requests_wait_while_warming_and_proceed_afterwards(self):
        gate = threading.Event()
        svc, _ = self._service()

        def slow_service():
            gate.wait(5)
            return svc
        warmup.start(slow_service)
        try:
            self.assertFalse(warmup._idle.is_set())
            waited = []
            t = threading.Thread(target=lambda: (warmup.wait(5), waited.append(True)))
            t.start()
            time.sleep(0.1)
            self.assertEqual(waited, [])          # still blocked
            gate.set()
            t.join(5)
            self.assertEqual(waited, [True])
        finally:
            gate.set()
            warmup.wait(5)

    def test_wait_returns_immediately_when_nothing_is_warming(self):
        self.assertTrue(warmup._idle.is_set())
        t0 = time.perf_counter()
        warmup.wait()
        self.assertLess(time.perf_counter() - t0, 0.5)


class TestBackendHooks(unittest.TestCase):
    def test_startup_hook_honours_the_flag(self):
        from backend import main
        self.assertIn(main._start_warmup, main.app.router.on_startup)
        with patch.object(main.warmup, "start") as start:
            with patch.object(main, "WARMUP_ON_START", True):
                main._start_warmup()
            start.assert_called_once_with(main._api_service)
        with patch.object(main.warmup, "start") as start, patch.object(main, "WARMUP_ON_START", False):
            main._start_warmup()
            start.assert_not_called()

    def test_service_is_built_once_even_when_requests_race_the_warmup(self):
        from backend import main
        built = []

        class Slow:
            def __init__(self):
                time.sleep(0.05)
                built.append(1)
        with patch.object(main, "DispenserAPIService", Slow), patch.object(main, "api_service", None):
            ts = [threading.Thread(target=main._api_service) for _ in range(6)]
            [t.start() for t in ts]
            [t.join() for t in ts]
        self.assertEqual(len(built), 1)

    def test_scan_and_ocr_routes_wait_for_warmup(self):
        main_src = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")
        ocr_src = (ROOT / "backend" / "ocr_routes.py").read_text(encoding="utf-8")
        self.assertIn("await asyncio.to_thread(warmup.wait)", main_src)   # does not block the event loop
        self.assertEqual(ocr_src.count("warmup.wait()"), 2)


class TestReactWiring(unittest.TestCase):
    """Static checks; the queue's behaviour itself is exercised by tests/test_camera_queue_js.py with Node."""

    def setUp(self):
        self.scan = (SRC / "TabletScan.jsx").read_text(encoding="utf-8")
        self.panel = (SRC / "ReverseSidePanel.jsx").read_text(encoding="utf-8")

    def test_no_component_fetches_camera_frames_directly(self):
        self.assertNotIn("camera/capture", self.scan)
        self.assertNotIn("camera/capture", self.panel)
        self.assertIn("fetchCameraFrame(API_URL", self.scan)

    def test_live_preview_backs_off_pauses_in_background_tabs_and_ignores_pauses(self):
        for text in ("document.hidden", "Math.min(1200 * 2 ** failures, 10000)", 'err.code !== "CAMERA_PAUSED"', "ctrl.abort()"):
            self.assertIn(text, self.scan, text)

    def test_stage_b_holds_exclusive_access_only_while_capturing(self):
        self.assertEqual(self.panel.count("beginExclusive()"), 1)
        self.assertIn("finally {\n        endExclusive();", self.panel.replace("\r\n", "\n"))

    def test_scan_post_is_never_retried_automatically(self):
        self.assertEqual(self.scan.count("/api/v1/devices/${devId}/inspection"), 1)   # one call site, only from the Run Scan handler
        self.assertNotIn("setTimeout(runScan", self.scan)


if __name__ == "__main__":
    unittest.main()
