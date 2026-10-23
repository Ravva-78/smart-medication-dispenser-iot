"""
Camera routes: the browser cannot call the ESP32 directly (CORS / private-network rules),
so the backend fetches the JPEG and relays the real bytes.

    GET /api/v1/camera/capture   -> image/jpeg (the camera's own bytes)
    GET /api/v1/camera/config    -> {"camera_url", "ip", "configured"}
    PUT /api/v1/camera/config    -> body {"ip": "<private LAN IPv4>"}; target is always http://<ip>/capture
"""
import threading

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from app import camera

router = APIRouter(prefix="/api/v1/camera", tags=["Camera"])

_capture_lock = threading.Lock()
_STATUS = {"not_configured": 503, "timeout": 504}  # everything else from the camera side is a 502


class CameraConfig(BaseModel):
    ip: str


def _config():
    url = camera.get_camera_url()
    ip = url[len("http://"):-len("/capture")] if url.startswith("http://") and url.endswith("/capture") else ""
    return {"camera_url": url, "ip": ip, "configured": bool(url)}


@router.get("/config")
def get_camera_config():
    return _config()


@router.put("/config")
def set_camera_config(body: CameraConfig):
    try:
        camera.set_camera_ip(body.ip)
    except ValueError as err:
        raise HTTPException(status_code=422, detail=str(err))
    return _config()


@router.get("/capture")
def capture():
    try:
        with _capture_lock:  # the ESP32 serves one request at a time; queue concurrent captures instead of colliding
            jpeg = camera.capture_jpeg()
    except camera.CameraError as err:
        raise HTTPException(status_code=_STATUS.get(err.kind, 502), detail={"kind": err.kind, "message": str(err)})
    return Response(content=jpeg, media_type="image/jpeg", headers={"Cache-Control": "no-store"})
