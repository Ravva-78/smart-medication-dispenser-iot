"""
ESP32-S3-CAM frame capture (laptop side).

The firmware (hardware/esp32_camera/esp32_camera.ino) only serves one JPEG per `GET /capture`;
all inference runs on the laptop. `capture_frame` returns a decoded BGR array and `capture_jpeg`
the validated JPEG bytes (used by the backend's /api/v1/camera/capture); both raise CameraError.

A capture is a read-only GET, so it is retried a bounded number of times inside one overall deadline
(config: CAMERA_RETRIES, CAMERA_DEADLINE_S). A frame is accepted only if every byte announced by
Content-Length arrived, a JPEG ends with its end-of-image marker, and it decodes; a partial or truncated
frame is never returned as a capture. Nothing here writes to a database.

The camera URL is ESP32_CAM_URL / ESP32_CAM_IP from config.py, or a runtime override set with
`set_camera_ip` (private LAN IPv4 only, fixed `http://<ip>/capture`) so a UI can configure it.

CLI check (no pipeline, optional save):  python -m app.camera [http://<esp32-ip>/capture] [--save frame.jpg]
"""
import ipaddress
import logging
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import requests
from urllib3.exceptions import ReadTimeoutError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import (CAMERA_CONNECT_TIMEOUT_S, CAMERA_DEADLINE_S, CAMERA_READ_TIMEOUT_S, CAMERA_RETRIES,
                    CAMERA_RETRY_BACKOFF_S, ESP32_CAM_URL)

logger = logging.getLogger(__name__)

MIN_SIDE_PX = 32  # anything smaller is not a usable photo of a blister strip
_runtime_url = ""  # set by set_camera_ip; overrides ESP32_CAM_URL for this process
_SOI, _EOI = b"\xff\xd8", b"\xff\xd9"
_RETRYABLE = {"timeout", "incomplete", "unreachable", "http_error", "empty", "invalid_image"}  # not "not_configured"


class CameraError(Exception):
    """Camera unreachable, timed out, returned an error, or returned an unusable image.

    kind: not_configured | timeout | unreachable | incomplete | http_error | empty | invalid_image
    """

    def __init__(self, message, kind="error"):
        super().__init__(message)
        self.kind = kind


def validate_camera_ip(ip):
    """Return a normalised private-LAN IPv4 string or raise ValueError (keeps the capture route from becoming an open proxy)."""
    try:
        addr = ipaddress.ip_address(str(ip).strip())
    except ValueError:
        raise ValueError(f"'{ip}' is not a valid IP address.")
    if addr.version != 4 or not addr.is_private or addr.is_loopback or addr.is_link_local \
            or addr.is_multicast or addr.is_unspecified:
        raise ValueError("Camera IP must be a private LAN IPv4 address (e.g. 192.168.x.x or 10.x.x.x).")
    return str(addr)


def set_camera_ip(ip):
    """Point captures at http://<ip>/capture; empty/None clears the override."""
    global _runtime_url
    _runtime_url = f"http://{validate_camera_ip(ip)}/capture" if ip else ""
    return _runtime_url


def get_camera_url():
    return _runtime_url or ESP32_CAM_URL or ""


def _classify(err, url):
    """Turn a requests error into the matching CameraError."""
    # requests reports a stall while reading the body as ConnectionError(ReadTimeoutError), not Timeout
    if isinstance(err, requests.exceptions.Timeout) or (err.args and isinstance(err.args[0], ReadTimeoutError)):
        return CameraError(f"Camera timed out ({url}). Check power, Wi-Fi and that the laptop is on the same network.", "timeout")
    if "IncompleteRead" in str(err):
        return CameraError(f"Camera dropped the connection mid-transfer ({err}). The Wi-Fi link is too weak or slow for a full frame; "
                           "move the ESP32 closer to the router/hotspot and retry.", "incomplete")
    return CameraError(f"Cannot reach camera at {url}: {err}", "unreachable")


def _download(url, timeout, deadline):
    """One GET. Returns the complete body or raises CameraError."""
    try:
        resp = requests.get(url, timeout=timeout, stream=True)
    except requests.exceptions.RequestException as err:
        raise _classify(err, url)
    try:
        if resp.status_code != 200:
            raise CameraError(f"Camera returned HTTP {resp.status_code} ({resp.text[:80]!r}).", "http_error")
        chunks = []
        try:
            for chunk in resp.iter_content(chunk_size=8192):
                chunks.append(chunk)
                if time.monotonic() > deadline:
                    raise CameraError("Camera did not finish sending the frame within the time limit.", "timeout")
        except requests.exceptions.RequestException as err:
            raise _classify(err, url)
        data = b"".join(chunks)
        announced = resp.headers.get("Content-Length")
    finally:
        resp.close()
    if not data:
        raise CameraError("Camera returned an empty response.", "empty")
    if announced and announced.isdigit() and len(data) != int(announced):
        raise CameraError(f"Camera sent {len(data)} of {announced} bytes: partial frame discarded.", "incomplete")
    if data.startswith(_SOI) and not data.rstrip(b"\x00").endswith(_EOI):
        raise CameraError("JPEG from the camera ends early (no end marker): truncated frame discarded.", "incomplete")
    return data


def _capture(url, timeout, retries, deadline_s, process):
    """Download + `process(data)` (validation/decoding), retrying read-only failures within the deadline."""
    url = (url or get_camera_url()).strip()
    if not url:
        raise CameraError("No camera URL configured. Set ESP32_CAM_URL (e.g. http://<esp32-ip>/capture).", "not_configured")
    if not url.startswith(("http://", "https://")):
        raise CameraError(f"Camera URL must start with http:// or https:// (got '{url}').", "not_configured")
    retries = CAMERA_RETRIES if retries is None else retries
    started = time.monotonic()
    deadline = started + (CAMERA_DEADLINE_S if deadline_s is None else deadline_s)
    attempt = 0
    while True:
        attempt += 1
        try:
            result = process(_download(url, timeout, deadline))
            if attempt > 1:
                logger.info("camera capture succeeded on attempt %d after %.1fs", attempt, time.monotonic() - started)
            return result
        except CameraError as err:
            out_of_time = time.monotonic() + CAMERA_RETRY_BACKOFF_S + 1.0 >= deadline
            if err.kind not in _RETRYABLE or attempt > retries or out_of_time:
                if attempt > 1:
                    raise CameraError(f"{err} (gave up after {attempt} attempts)", err.kind) from err
                raise
            logger.warning("camera capture attempt %d failed (%s); retrying", attempt, err.kind)
            time.sleep(CAMERA_RETRY_BACKOFF_S)


def _decode(content):
    frame = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise CameraError(f"Camera response ({len(content)} bytes) is not a decodable image.", "invalid_image")
    if min(frame.shape[:2]) < MIN_SIDE_PX:
        raise CameraError(f"Camera image is too small ({frame.shape[1]}x{frame.shape[0]} px).", "invalid_image")
    return frame


def _check_jpeg(content):
    if not content.startswith(_SOI):
        raise CameraError("Camera response is not a JPEG image.", "invalid_image")
    _decode(content)
    return content


def capture_frame(url=None, timeout=(CAMERA_CONNECT_TIMEOUT_S, CAMERA_READ_TIMEOUT_S), retries=None, deadline_s=None):
    return _capture(url, timeout, retries, deadline_s, _decode)


def capture_jpeg(url=None, timeout=(CAMERA_CONNECT_TIMEOUT_S, CAMERA_READ_TIMEOUT_S), retries=None, deadline_s=None):
    """The camera's own JPEG bytes, after checking they really are a complete, decodable JPEG."""
    return _capture(url, timeout, retries, deadline_s, _check_jpeg)


if __name__ == "__main__":
    args = sys.argv[1:]
    save = args[args.index("--save") + 1] if "--save" in args else None
    target = next((a for a in args if a.startswith("http")), None)
    try:
        img = capture_frame(target)
    except CameraError as err:
        print(f"CAPTURE FAILED: {err}")
        sys.exit(1)
    print(f"CAPTURE OK: {img.shape[1]}x{img.shape[0]} px")
    if save:
        cv2.imwrite(save, img)
        print(f"saved to {save}")
