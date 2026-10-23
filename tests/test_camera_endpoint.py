"""
Backend camera routes (/api/v1/camera/*). The ESP32 HTTP call is mocked; these prove relaying,
error mapping and input validation, not live hardware. The React file is only checked statically
(the UI project has no test runner).
"""
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np
import requests
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import camera
from backend.camera_routes import router

ROOT = Path(__file__).resolve().parent.parent
JPEG = cv2.imencode(".jpg", np.tile(np.arange(240, dtype=np.uint8)[:, None, None], (1, 320, 3)))[1].tobytes()
PNG = cv2.imencode(".png", np.zeros((64, 64, 3), dtype=np.uint8))[1].tobytes()


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


_Resp = FakeResponse


class TestCameraEndpoint(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)
        camera.set_camera_ip("")
        patcher = patch("app.camera.ESP32_CAM_URL", "")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(camera.set_camera_ip, "")

    def _configure(self, ip="192.168.1.50"):
        self.assertEqual(self.client.put("/api/v1/camera/config", json={"ip": ip}).status_code, 200)

    # ── capture ────────────────────────────────────────────────────────────
    @patch("app.camera.requests.get")
    def test_success_returns_the_cameras_exact_jpeg_bytes(self, get):
        get.return_value = _Resp(JPEG)
        self._configure()
        r = self.client.get("/api/v1/camera/capture")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers["content-type"], "image/jpeg")
        self.assertEqual(r.headers["cache-control"], "no-store")
        self.assertEqual(r.content, JPEG)
        self.assertEqual(get.call_args.args[0], "http://192.168.1.50/capture")
        self.assertEqual(get.call_args.kwargs["timeout"], (camera.CAMERA_CONNECT_TIMEOUT_S, camera.CAMERA_READ_TIMEOUT_S))

    def test_not_configured_is_503_and_makes_no_request(self):
        with patch("app.camera.requests.get") as get:
            r = self.client.get("/api/v1/camera/capture")
            get.assert_not_called()
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json()["detail"]["kind"], "not_configured")

    @patch("app.camera.requests.get", side_effect=requests.exceptions.ConnectTimeout())
    def test_timeout_is_504(self, _):
        self._configure()
        r = self.client.get("/api/v1/camera/capture")
        self.assertEqual((r.status_code, r.json()["detail"]["kind"]), (504, "timeout"))

    def test_stall_while_downloading_body_is_a_timeout_not_unreachable(self):
        # real requests behaviour: ConnectionError wrapping urllib3's ReadTimeoutError
        from urllib3.exceptions import ReadTimeoutError
        self._configure()
        err = requests.exceptions.ConnectionError(ReadTimeoutError(None, None, "Read timed out."))
        with patch("app.camera.requests.get", side_effect=err):
            r = self.client.get("/api/v1/camera/capture")
        self.assertEqual((r.status_code, r.json()["detail"]["kind"]), (504, "timeout"))

    def test_connection_dropped_mid_transfer_is_reported_as_incomplete(self):
        # observed on the live camera: 'Connection broken: IncompleteRead(24412 bytes read, 1387 more expected)'
        self._configure()
        err = requests.exceptions.ConnectionError("('Connection broken: IncompleteRead(24412 bytes read, 1387 more expected)',)")
        with patch("app.camera.requests.get", side_effect=err):
            r = self.client.get("/api/v1/camera/capture")
        self.assertEqual((r.status_code, r.json()["detail"]["kind"]), (502, "incomplete"))
        self.assertIn("mid-transfer", r.json()["detail"]["message"])

    @patch("app.camera.requests.get", side_effect=requests.exceptions.ConnectionError("refused"))
    def test_unreachable_is_502(self, _):
        self._configure()
        r = self.client.get("/api/v1/camera/capture")
        self.assertEqual((r.status_code, r.json()["detail"]["kind"]), (502, "unreachable"))

    @patch("app.camera.requests.get")
    def test_camera_http_error_is_502(self, get):
        get.return_value = _Resp(b"x", status=500, text="Camera capture failed")
        self._configure()
        r = self.client.get("/api/v1/camera/capture")
        self.assertEqual((r.status_code, r.json()["detail"]["kind"]), (502, "http_error"))

    @patch("app.camera.requests.get")
    def test_bad_images_are_502_never_relayed(self, get):
        self._configure()
        cases = {
            "empty": b"",
            "not a jpeg (PNG)": PNG,
            "jpeg header but corrupt": b"\xff\xd8\xff\xe0" + b"garbage" * 10,
            "text": b"hello",
        }
        for name, body in cases.items():
            with self.subTest(name):
                get.return_value = _Resp(body)
                r = self.client.get("/api/v1/camera/capture")
                self.assertEqual(r.status_code, 502)
                self.assertNotEqual(r.headers["content-type"], "image/jpeg")
                self.assertIn("message", r.json()["detail"])

    def test_concurrent_captures_never_overlap_at_the_camera(self):
        import threading
        import time
        state = {"active": 0, "max": 0}

        def slow_get(*a, **k):
            state["active"] += 1
            state["max"] = max(state["max"], state["active"])
            time.sleep(0.05)
            state["active"] -= 1
            return _Resp(JPEG)

        self._configure()
        with patch("app.camera.requests.get", side_effect=slow_get):
            codes = []
            threads = [threading.Thread(target=lambda: codes.append(self.client.get("/api/v1/camera/capture").status_code)) for _ in range(4)]
            [t.start() for t in threads]
            [t.join() for t in threads]
        self.assertEqual(codes, [200] * 4)
        self.assertEqual(state["max"], 1)

    # ── configuration ──────────────────────────────────────────────────────
    def test_config_roundtrip(self):
        self.assertEqual(self.client.get("/api/v1/camera/config").json(), {"camera_url": "", "ip": "", "configured": False})
        self._configure("10.69.42.228")
        self.assertEqual(self.client.get("/api/v1/camera/config").json(),
                         {"camera_url": "http://10.69.42.228/capture", "ip": "10.69.42.228", "configured": True})

    def test_changed_ip_is_what_the_backend_actually_fetches(self):
        with patch("app.camera.requests.get", return_value=_Resp(JPEG)) as get:
            self._configure("192.168.1.50")
            self.client.get("/api/v1/camera/capture")
            self._configure("10.0.0.7")
            self.client.get("/api/v1/camera/capture")
        self.assertEqual([c.args[0] for c in get.call_args_list],
                         ["http://192.168.1.50/capture", "http://10.0.0.7/capture"])

    def test_env_url_is_the_default_and_runtime_ip_overrides_it(self):
        with patch("app.camera.ESP32_CAM_URL", "http://192.168.9.9/capture"):
            self.assertEqual(self.client.get("/api/v1/camera/config").json()["ip"], "192.168.9.9")
            self._configure("10.0.0.7")
            self.assertEqual(self.client.get("/api/v1/camera/config").json()["ip"], "10.0.0.7")

    def test_not_an_open_proxy(self):
        for bad in ["example.com", "http://10.0.0.1/x", "10.0.0.1/../etc", "8.8.8.8", "127.0.0.1",
                    "169.254.169.254", "0.0.0.0", "224.0.0.1", "::1", "", "300.1.1.1"]:
            with self.subTest(bad):
                r = self.client.put("/api/v1/camera/config", json={"ip": bad})
                self.assertIn(r.status_code, (200, 422))
                if r.status_code == 200:  # only the empty string is accepted: it clears the override
                    self.assertEqual(bad, "")
        self.assertFalse(self.client.get("/api/v1/camera/config").json()["configured"])

    def test_missing_ip_field_is_rejected(self):
        self.assertEqual(self.client.put("/api/v1/camera/config", json={}).status_code, 422)


class TestWiring(unittest.TestCase):
    def test_backend_app_registers_camera_routes(self):
        from backend.main import app
        paths = app.openapi()["paths"]
        self.assertIn("/api/v1/camera/capture", paths)
        self.assertIn("/api/v1/camera/config", paths)
        self.assertEqual(TestClient(app).get("/api/v1/camera/config").status_code, 200)

    def test_tabletscan_uses_backend_not_esp32_directly(self):
        src = (ROOT / "medidispense-ui" / "src" / "pages" / "TabletIdentification" / "TabletScan.jsx").read_text(encoding="utf-8")
        queue = (ROOT / "medidispense-ui" / "src" / "pages" / "TabletIdentification" / "cameraCapture.js").read_text(encoding="utf-8")
        self.assertIn("/api/v1/camera/capture", queue)           # frames are fetched through the shared one-at-a-time queue
        self.assertIn("fetchCameraFrame(", src)
        self.assertIn("/api/v1/camera/config", src)
        self.assertNotIn("10.196.64.228", src)
        self.assertNotIn("http://${esp32Ip}", src)  # no direct browser -> ESP32 fetch


if __name__ == "__main__":
    unittest.main()
