"""
Bounded capture retries, overall deadline and frame-integrity checks (HTTP mocked; no real camera).
A capture is a read-only GET: retries never write anything and a partial or truncated frame is never
returned as a successful capture.
"""
import unittest
from pathlib import Path
from unittest.mock import patch

import requests
from fastapi import FastAPI
from fastapi.testclient import TestClient
from urllib3.exceptions import ReadTimeoutError

from app import camera
from app.camera import CameraError, capture_frame, capture_jpeg
from backend.camera_routes import router
from tests.test_camera import FakeResponse, _jpeg

URL = "http://192.0.2.10/capture"
JPEG = _jpeg()


def partial():
    return FakeResponse(JPEG[: len(JPEG) // 2], headers={"Content-Length": str(len(JPEG))})


_SLEEP = patch("app.camera.time.sleep")


def setUpModule():
    _SLEEP.start()


def tearDownModule():
    _SLEEP.stop()


class TestRetries(unittest.TestCase):
    @patch("app.camera.requests.get")
    def test_incomplete_then_good_frame_succeeds_on_retry(self, get):
        get.side_effect = [partial(), FakeResponse(JPEG)]
        self.assertEqual(capture_jpeg(URL), JPEG)
        self.assertEqual(get.call_count, 2)
        self.assertTrue(all(c.args[0] == URL and c.kwargs["stream"] is True for c in get.call_args_list))

    @patch("app.camera.requests.get")
    def test_partial_frames_are_never_returned_and_attempts_are_bounded(self, get):
        get.side_effect = lambda *a, **k: partial()
        with self.assertRaises(CameraError) as ctx:
            capture_jpeg(URL)
        self.assertEqual(ctx.exception.kind, "incomplete")
        self.assertIn("gave up after 3 attempts", str(ctx.exception))
        self.assertEqual(get.call_count, 3)      # 1 try + CAMERA_RETRIES (2)

    @patch("app.camera.requests.get")
    def test_retries_zero_restores_single_attempt_behaviour(self, get):
        get.side_effect = lambda *a, **k: partial()
        with self.assertRaises(CameraError):
            capture_jpeg(URL, retries=0)
        self.assertEqual(get.call_count, 1)

    @patch("app.camera.requests.get")
    def test_content_length_mismatch_is_discarded(self, get):
        get.return_value = partial()
        with self.assertRaisesRegex(CameraError, "partial frame discarded"):
            capture_frame(URL, retries=0)

    @patch("app.camera.requests.get")
    def test_jpeg_without_end_marker_is_discarded_even_if_length_matches(self, get):
        get.return_value = FakeResponse(JPEG[:-2])            # Content-Length matches the shortened body
        with self.assertRaisesRegex(CameraError, "no end marker"):
            capture_jpeg(URL, retries=0)

    @patch("app.camera.requests.get")
    def test_zero_padding_after_end_marker_is_accepted_unchanged(self, get):
        get.return_value = FakeResponse(JPEG + b"\x00\x00")
        self.assertEqual(capture_jpeg(URL), JPEG + b"\x00\x00")

    @patch("app.camera.requests.get")
    def test_transient_http_error_and_bad_image_are_retried(self, get):
        get.side_effect = [FakeResponse(b"x", status=500, text="fail"), FakeResponse(b"not an image"), FakeResponse(JPEG)]
        self.assertEqual(capture_jpeg(URL), JPEG)
        self.assertEqual(get.call_count, 3)

    @patch("app.camera.requests.get")
    def test_stall_while_downloading_is_a_timeout_and_is_retried(self, get):
        class Stalls(FakeResponse):
            def iter_content(self, chunk_size=8192):
                yield self.content[:100]
                raise requests.exceptions.ConnectionError(ReadTimeoutError(None, None, "Read timed out."))
        get.side_effect = [Stalls(JPEG), FakeResponse(JPEG)]
        self.assertEqual(capture_jpeg(URL), JPEG)
        get.side_effect = lambda *a, **k: Stalls(JPEG)
        with self.assertRaises(CameraError) as ctx:
            capture_jpeg(URL)
        self.assertEqual(ctx.exception.kind, "timeout")

    @patch("app.camera.requests.get")
    def test_configuration_errors_are_not_retried(self, get):
        with patch("app.camera.ESP32_CAM_URL", ""), patch.object(camera, "_runtime_url", ""):
            with self.assertRaises(CameraError) as ctx:
                capture_jpeg()
        self.assertEqual(ctx.exception.kind, "not_configured")
        with self.assertRaises(CameraError):
            capture_jpeg("ftp://x/capture")
        get.assert_not_called()


class TestDeadline(unittest.TestCase):
    @patch("app.camera.requests.get")
    def test_slow_download_stops_at_the_deadline_without_further_retries(self, get):
        clock = {"now": 1000.0}

        class Slow(FakeResponse):
            def iter_content(self, chunk_size=8192):
                for i in range(0, len(self.content), 1024):
                    clock["now"] += 5.0                 # 5 s per KB: far too slow
                    yield self.content[i:i + 1024]

        get.side_effect = lambda *a, **k: Slow(JPEG)
        with patch("app.camera.time.monotonic", lambda: clock["now"]):
            with self.assertRaises(CameraError) as ctx:
                capture_jpeg(URL, deadline_s=10, retries=5)
        self.assertEqual(ctx.exception.kind, "timeout")
        self.assertEqual(get.call_count, 1)            # no new attempt once the budget is spent


class TestNoSideEffects(unittest.TestCase):
    def test_capture_code_is_read_only(self):
        src = (Path(__file__).resolve().parent.parent / "app" / "camera.py").read_text(encoding="utf-8")
        for forbidden in ("requests.post", "requests.put", "requests.delete", "import database", "from database", "insert_one", "open("):
            self.assertNotIn(forbidden, src, forbidden)

    @patch("app.camera.requests.get")
    def test_relay_never_serves_a_partial_frame_as_an_image(self, get):
        get.side_effect = lambda *a, **k: partial()
        app = FastAPI()
        app.include_router(router)
        camera.set_camera_ip("192.168.1.50")
        try:
            r = TestClient(app).get("/api/v1/camera/capture")
        finally:
            camera.set_camera_ip("")
        self.assertEqual(r.status_code, 502)
        self.assertNotEqual(r.headers["content-type"], "image/jpeg")
        self.assertEqual(r.json()["detail"]["kind"], "incomplete")


if __name__ == "__main__":
    unittest.main()
