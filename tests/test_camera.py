"""
ESP32 capture client tests. The HTTP layer is mocked: no real camera is involved,
so these prove error handling and decoding, not live capture.
"""
import unittest
from unittest.mock import patch, MagicMock

import cv2
import numpy as np
import requests

from app import camera
from app.camera import capture_frame, CameraError
from tests.test_verification import _pipe

URL = "http://192.0.2.10/capture"  # TEST-NET address, never routable


def _jpeg(w=320, h=240):
    img = np.tile(np.arange(h, dtype=np.uint8)[:, None, None], (1, w, 3))
    return cv2.imencode(".jpg", img)[1].tobytes()


class FakeResponse:
    """Streaming-capable stand-in for requests.Response (the capture client reads the body in chunks)."""

    def __init__(self, content=b"", status=200, text="", headers=None):
        self.content, self.status_code, self.text = content, status, text
        self.headers = {"Content-Length": str(len(content))} if headers is None else headers

    def iter_content(self, chunk_size=8192):
        for i in range(0, len(self.content), chunk_size):
            yield self.content[i:i + chunk_size]

    def close(self):
        pass


_SLEEP = patch("app.camera.time.sleep")   # retries back off between attempts; keep the tests instant


def setUpModule():
    _SLEEP.start()


def tearDownModule():
    _SLEEP.stop()


_resp = FakeResponse


class TestCaptureFrame(unittest.TestCase):
    @patch("app.camera.requests.get")
    def test_valid_jpeg_is_decoded_with_timeouts(self, get):
        get.return_value = _resp(_jpeg())
        frame = capture_frame(URL)
        self.assertEqual(frame.shape, (240, 320, 3))
        self.assertEqual(get.call_args.kwargs["timeout"], (camera.CAMERA_CONNECT_TIMEOUT_S, camera.CAMERA_READ_TIMEOUT_S))

    @patch("app.camera.requests.get")
    def test_empty_response_rejected(self, get):
        get.return_value = _resp(b"")
        with self.assertRaisesRegex(CameraError, "empty"):
            capture_frame(URL)

    @patch("app.camera.requests.get")
    def test_undecodable_bytes_rejected(self, get):
        get.return_value = _resp(b"not an image")
        with self.assertRaisesRegex(CameraError, "decodable"):
            capture_frame(URL)

    @patch("app.camera.requests.get")
    def test_tiny_image_rejected(self, get):
        get.return_value = _resp(_jpeg(8, 8))
        with self.assertRaisesRegex(CameraError, "too small"):
            capture_frame(URL)

    @patch("app.camera.requests.get")
    def test_http_error_rejected(self, get):
        get.return_value = _resp(b"x", status=500, text="Camera capture failed")
        with self.assertRaisesRegex(CameraError, "HTTP 500"):
            capture_frame(URL)

    @patch("app.camera.requests.get", side_effect=requests.exceptions.ConnectTimeout())
    def test_timeout_has_clear_message(self, _):
        with self.assertRaisesRegex(CameraError, "timed out"):
            capture_frame(URL)

    @patch("app.camera.requests.get", side_effect=requests.exceptions.ConnectionError("refused"))
    def test_connection_failure_has_clear_message(self, _):
        with self.assertRaisesRegex(CameraError, "Cannot reach camera"):
            capture_frame(URL)

    def test_missing_or_malformed_url_rejected_without_network(self):
        with patch("app.camera.ESP32_CAM_URL", ""), patch("app.camera.requests.get") as get:
            with self.assertRaisesRegex(CameraError, "No camera URL"):
                capture_frame("")
            with self.assertRaisesRegex(CameraError, "http"):
                capture_frame("192.168.1.5/capture")
            get.assert_not_called()


class TestCameraToPipelineBoundary(unittest.TestCase):
    @patch("app.camera.requests.get")
    def test_captured_frame_runs_through_existing_pipeline(self, get):
        get.return_value = _resp(_jpeg(700, 400))
        result = _pipe(["present"] * 10).run(capture_frame(URL))
        self.assertEqual(result.verification, "VERIFIED")
        self.assertEqual(result.total, 10)

    @patch("app.camera.requests.get", side_effect=requests.exceptions.ConnectTimeout())
    def test_failed_capture_never_reaches_pipeline_or_invents_counts(self, _):
        pipe = _pipe(["present"] * 10)
        try:
            result = pipe.run(capture_frame(URL))
        except CameraError:
            result = None
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
