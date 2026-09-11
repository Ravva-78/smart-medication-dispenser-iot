"""
FastAPI REST API Application Entry Point.

Purpose:
    Exposes production-ready RESTful endpoints for IoT Devices, Patients, Prescriptions, Schedules,
    and Full AI Subsystem Inspections with MongoDB Atlas Persistence.

Core AI Endpoints (unchanged):
    - GET  /
    - GET  /api/v1/health
    - POST /api/v1/devices/{device_id}/inspection
    - GET  /api/v1/patients/{patient_id}
    - GET  /api/v1/patients/{patient_id}/prescriptions
    - GET  /api/v1/patients/{patient_id}/schedule
    - GET  /api/v1/alerts/{patient_id}

Frontend Integration Endpoints (added for medidispense-ui):
    - GET/POST/PUT/DELETE  /patients
    - GET/POST/PUT/DELETE  /medications
    - GET/POST/PATCH/DELETE /devices
    - GET/PATCH/DELETE     /alerts
    - GET/POST/PUT/DELETE  /prescriptions
    - GET/PUT              /schedules
    - GET                  /audits
    - GET/POST             /reports
    - GET/PUT              /settings
    - GET                  /dispense
    - GET                  /verifications
"""

import sys
import uuid
import logging
import time
import concurrent.futures
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Body
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
import cv2

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.server import DispenserAPIService
from database.connection import get_db
from database.repositories import (
    DeviceRepository,
    PatientRepository,
    PrescriptionRepository,
    ScheduleRepository,
    InspectionRepository,
    ComplianceRepository,
    AlertRepository,
    MedicineCatalogueRepository,
)

app = FastAPI(
    title="Medicine Dispenser & Compliance API",
    description="IoT Pill Dispenser AI Pipeline & Clinical Compliance Engine — Frontend + Core API",
    version="2.0.0",
)

# CORS — allow React dev server and any frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Singleton service and repositories ───────────────────────────────────────
api_service = None
logger = logging.getLogger(__name__)
_db_unavailable_until = 0.0
_memory_db = None


class _MemoryInsertResult:
    inserted_id = "memory_inserted_id"
    inserted_ids = ["memory_inserted_id"]


class _MemoryUpdateResult:
    modified_count = 1


class _MemoryCursor(list):
    def sort(self, key, direction=-1):
        reverse = direction == -1
        return _MemoryCursor(sorted(self, key=lambda row: str(row.get(key, "")), reverse=reverse))

    def limit(self, count):
        return _MemoryCursor(self[:count])


class _MemoryCollection:
    def __init__(self, rows=None):
        self.rows = [dict(row) for row in (rows or [])]

    def _matches(self, row, query):
        for key, expected in (query or {}).items():
            actual = row.get(key)
            if isinstance(expected, dict) and "$in" in expected:
                if actual not in expected["$in"]:
                    return False
            elif actual != expected:
                return False
        return True

    def find_one(self, query=None, projection=None, sort=None):
        for row in self.rows:
            if self._matches(row, query):
                return dict(row)
        return None

    def find(self, query=None, projection=None):
        return _MemoryCursor([dict(row) for row in self.rows if self._matches(row, query)])

    def insert_one(self, row):
        self.rows.append(dict(row))
        return _MemoryInsertResult()

    def insert_many(self, rows):
        self.rows.extend(dict(row) for row in rows)
        return _MemoryInsertResult()

    def update_one(self, query, update, upsert=False):
        for row in self.rows:
            if self._matches(row, query):
                row.update(update.get("$set", {}))
                return _MemoryUpdateResult()
        if upsert:
            created = {k: v for k, v in (query or {}).items() if not isinstance(v, dict)}
            created.update(update.get("$set", {}))
            self.rows.append(created)
        return _MemoryUpdateResult()

    def update_many(self, query, update):
        for row in self.rows:
            if self._matches(row, query):
                row.update(update.get("$set", {}))
        return _MemoryUpdateResult()

    def delete_one(self, query=None):
        for index, row in enumerate(self.rows):
            if self._matches(row, query):
                del self.rows[index]
                break

    def delete_many(self, query=None):
        self.rows = [row for row in self.rows if not self._matches(row, query)]

    def count_documents(self, query=None):
        return len(self.find(query))


class _MemoryDB(dict):
    def __getitem__(self, name):
        if name not in self:
            self[name] = _MemoryCollection()
        return dict.__getitem__(self, name)


def _fallback_db():
    global _memory_db
    if _memory_db is None:
        _memory_db = _MemoryDB({
            "patients": _MemoryCollection(DEFAULT_PATIENTS),
            "devices": _MemoryCollection(DEFAULT_DEVICES),
            "prescriptions": _MemoryCollection(DEFAULT_PRESCRIPTIONS),
            "daily_schedule": _MemoryCollection(),
            "alerts": _MemoryCollection(),
            "scan_baselines": _MemoryCollection(),
            "inspection_sessions": _MemoryCollection(),
            "inspection_results": _MemoryCollection(),
            "clinical_decisions": _MemoryCollection(),
            "compliance_decisions": _MemoryCollection(),
        })
    return _memory_db


def _api_service() -> DispenserAPIService:
    global api_service
    if api_service is None:
        api_service = DispenserAPIService()
    return api_service

def _db():
    global _db_unavailable_until
    if time.monotonic() < _db_unavailable_until:
        return _fallback_db()
    try:
        return get_db()
    except Exception as exc:
        _db_unavailable_until = time.monotonic() + 15.0
        logger.warning("MongoDB unavailable; using in-memory fallback DB: %s", exc)
        return _fallback_db()

def _patients():    return PatientRepository(_db())
def _devices():     return DeviceRepository(_db())
def _prescriptions(): return PrescriptionRepository(_db())
def _schedules():   return ScheduleRepository(_db())
def _alerts():      return AlertRepository(_db())
def _meds():        return MedicineCatalogueRepository(_db())
def _inspections(): return InspectionRepository(_db())
def _compliance():  return ComplianceRepository(_db())

# In-memory lightweight singletons for cosmetic pages
_reports_store: List[Dict] = []
_settings_store: Dict = {
    "hospitalName": "General Hospital",
    "wardCount": 12,
    "deviceCount": 45,
    "alertThresholds": {"criticalStock": 10, "lowStock": 50},
    "dashboardRefreshInterval": 30,
    "themePreference": "dark",
}

# Default fallback datasets for graceful offline degradation
DEFAULT_PATIENTS = [
    {
        "patient_id": "PAT-ARJUN-01",
        "name": "Arjun Mehta",
        "ward": "Ward A",
        "bed_number": "Bed 12",
        "age": 45,
        "gender": "Male",
        "doctor": "Dr. Sarah Chen",
        "caregiver_contact": "+91-98765-43210",
        "medicine_name": "Paracetamol 500mg",
        "status": "Active",
        "next_dose": "09:30 IST",
    },
    {
        "patient_id": "PAT-MEENA-01",
        "name": "Meena Pillai",
        "ward": "Ward B",
        "bed_number": "Bed 07",
        "age": 62,
        "gender": "Female",
        "doctor": "Dr. Ramesh Gupta",
        "caregiver_contact": "+91-98765-43211",
        "medicine_name": "Metformin 500mg",
        "status": "Active",
        "next_dose": "09:30 IST",
    },
]

DEFAULT_DEVICES = [
    {
        "device_id": "DEV-ARJUN-01",
        "ward": "Ward A",
        "room": "Room A-12",
        "status": "Online",
        "battery_level": 92,
        "slots_used": 0,
        "slots_total": 10,
        "patient_id": "PAT-ARJUN-01",
        "camera_id": "CAM-01",
        "last_seen": "Just now",
    },
    {
        "device_id": "DEV-MEENA-01",
        "ward": "Ward B",
        "room": "Room B-07",
        "status": "Online",
        "battery_level": 88,
        "slots_used": 0,
        "slots_total": 10,
        "patient_id": "PAT-MEENA-01",
        "camera_id": "CAM-02",
        "last_seen": "Just now",
    },
]

DEFAULT_MEDS = [
    {"medicine_id": "MED-001", "brand": "Paracetamol", "strength": "500mg", "current_stock": 150, "low_stock_threshold": 20, "expiry_date": "2027-12-31"},
    {"medicine_id": "MED-002", "brand": "Metformin", "strength": "500mg", "current_stock": 90, "low_stock_threshold": 15, "expiry_date": "2027-06-30"},
    {"medicine_id": "MED-003", "brand": "Amoxicillin", "strength": "250mg", "current_stock": 45, "low_stock_threshold": 10, "expiry_date": "2026-11-30"},
    {"medicine_id": "MED-004", "brand": "Atorvastatin", "strength": "10mg", "current_stock": 60, "low_stock_threshold": 15, "expiry_date": "2028-01-31"},
]

DEFAULT_ALERTS = []

DEFAULT_PRESCRIPTIONS = [
    {
        "prescription_id": "RX-ARJUN-01",
        "patient_id": "PAT-ARJUN-01",
        "patient_name": "Arjun Mehta",
        "medicine_name": "Paracetamol",
        "strength": "500mg",
        "frequency": "Three times daily",
        "start_date": "2026-08-01",
        "end_date": "2026-08-30",
        "doctor": "Dr. Sarah Chen",
        "active": True,
    },
    {
        "prescription_id": "RX-MEENA-01",
        "patient_id": "PAT-MEENA-01",
        "patient_name": "Meena Pillai",
        "medicine_name": "Metformin",
        "strength": "500mg",
        "frequency": "Twice daily",
        "start_date": "2026-08-01",
        "end_date": "2026-08-30",
        "doctor": "Dr. Ramesh Gupta",
        "active": True,
    },
]

def _ist_now() -> str:
    """Return current IST timestamp as ISO string."""
    ist = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist).isoformat()


_NO_FALLBACK = object()


def _safe_db_call(fn, fallback=_NO_FALLBACK):
    """
    Execute a DB callable safely.
    Returns `fallback` (default []) if MongoDB Atlas is unreachable, SSL fails, or timed out.
    This prevents 500 errors from propagating to the React frontend.
    """
    if fallback is _NO_FALLBACK:
        fallback = []
    global _db_unavailable_until
    if time.monotonic() < _db_unavailable_until:
        return fallback
    try:
        res = fn()
        if res is None:
            return fallback
        return res
    except Exception as e:
        import logging
        _db_unavailable_until = time.monotonic() + 15.0
        logging.getLogger("backend.main").warning("MongoDB call failed (using fallback): %s", e)
        return fallback


def _index_by(items: List[Dict[str, Any]], key: str) -> Dict[str, Dict[str, Any]]:
    return {item.get(key): item for item in items if item.get(key)}


def _patient_lookup(db) -> Dict[str, Dict[str, Any]]:
    patients = _safe_db_call(lambda: list(db["patients"].find({}, {"_id": 0})), fallback=None)
    if patients is None:
        patients = DEFAULT_PATIENTS
    return _index_by(patients, "patient_id")


def _device_lookup(db) -> Dict[str, Dict[str, Any]]:
    devices = _safe_db_call(lambda: list(db["devices"].find({}, {"_id": 0})), fallback=None)
    if devices is None:
        devices = DEFAULT_DEVICES
    return _index_by(devices, "device_id")


def _prescription_lookup(db) -> Dict[str, List[Dict[str, Any]]]:
    prescriptions = _safe_db_call(lambda: list(db["prescriptions"].find({}, {"_id": 0})), fallback=None)
    if prescriptions is None:
        prescriptions = DEFAULT_PRESCRIPTIONS
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for rx in prescriptions:
        grouped.setdefault(rx.get("patient_id", ""), []).append(rx)
    return grouped


def _patient_name(patient_id: str, patients: Dict[str, Dict[str, Any]]) -> str:
    patient = patients.get(patient_id, {})
    return patient.get("name") or patient_id or "-"


def _patient_ward(patient_id: str, patients: Dict[str, Dict[str, Any]], fallback: str = "") -> str:
    patient = patients.get(patient_id, {})
    return patient.get("ward") or fallback or "-"


def _device_for_patient(patient_id: str, devices: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    for device in devices.values():
        if device.get("patient_id") == patient_id:
            return device
    return {}


def _ensure_patient_device(db, patient_id: str, patient: Dict[str, Any], requested_device_id: str = "") -> Dict[str, Any]:
    devices = _device_lookup(db)
    existing = _device_for_patient(patient_id, devices)
    if existing:
        return existing

    key = _patient_key(patient_id)
    device_id = _display_value(requested_device_id) or _display_value(patient.get("device_id")) or f"DEV-{key}"
    doc = {
        "device_id": device_id,
        "patient_id": patient_id,
        "ward": patient.get("ward", ""),
        "room": patient.get("bed_number", patient.get("bedNumber", "Bed 1")),
        "status": "Online",
        "battery_level": 98,
        "slots_used": 0,
        "slots_total": 10,
        "camera_id": f"CAM-{key[-4:]}",
        "last_seen": "Just now",
        "created_at": _ist_now(),
    }
    _safe_db_call(lambda: db["devices"].update_one({"device_id": device_id}, {"$set": doc}, upsert=True))
    return doc


def _patient_schedule_rows(db, patient_id: str) -> List[Dict[str, Any]]:
    rows = _safe_db_call(
        lambda: list(db["daily_schedule"].find({"patient_id": patient_id}, {"_id": 0})),
        fallback=[],
    )
    return rows if isinstance(rows, list) else []


def _time_value(value: Any) -> str:
    if not value:
        return ""
    text = str(value)
    if "T" in text:
        return text.split("T", 1)[1][:8]
    return text


def _display_value(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text or text in {"-", "—", "â€”", "â", "None", "null", "NULL", "No Schedule", "No schedule"}:
        return ""
    return text


def _split_medication_text(value: Any) -> tuple[str, str]:
    med_input = _display_value(value) or "Medication 500mg"
    parts = med_input.split()
    if len(parts) > 1 and any(unit in parts[-1].lower() for unit in ["mg", "mcg", "g", "ml"]):
        return " ".join(parts[:-1]), parts[-1]
    return med_input, "500mg"


def _patient_key(patient_id: str) -> str:
    return "".join(c.upper() for c in str(patient_id or "") if c.isalnum())[-8:] or uuid.uuid4().hex[:6].upper()


def _upsert_patient_prescription(db, patient_id: str, patient: Dict[str, Any], medication: Any) -> Optional[Dict[str, Any]]:
    med_text = _display_value(medication)
    if not med_text:
        return None

    brand, strength = _split_medication_text(med_text)
    existing = _safe_db_call(
        lambda: db["prescriptions"].find_one({"patient_id": patient_id, "active": True}, {"_id": 0}),
        fallback=None,
    ) or {}
    rx_id = existing.get("prescription_id") or f"RX-{_patient_key(patient_id)}"
    patient_name = _display_value(patient.get("name")) or patient_id
    doc = {
        "prescription_id": rx_id,
        "patient_id": patient_id,
        "patient_name": patient_name,
        "medicine_name": brand,
        "strength": strength,
        "dosage_form": existing.get("dosage_form", "Tablet"),
        "doses_per_day": existing.get("doses_per_day", 1),
        "frequency": existing.get("frequency") or "Once daily",
        "start_date": existing.get("start_date") or _ist_now().split("T")[0],
        "end_date": existing.get("end_date") or "2026-12-31",
        "doctor": _display_value(patient.get("doctor")) or existing.get("doctor", ""),
        "active": True,
        "updated_at": _ist_now(),
    }
    if not existing:
        doc["created_at"] = _ist_now()
    _safe_db_call(lambda: db["prescriptions"].update_one({"prescription_id": rx_id}, {"$set": doc}, upsert=True))
    return doc


def _upsert_patient_schedule(db, patient_id: str, patient: Dict[str, Any], rx: Dict[str, Any], next_time: Any) -> Optional[Dict[str, Any]]:
    target_time = _display_value(next_time)
    if ":" not in target_time:
        return None

    today = _ist_now().split("T")[0]
    existing = _safe_db_call(
        lambda: db["daily_schedule"].find_one(
            {"patient_id": patient_id, "date": today, "status": {"$in": ["PENDING", "MISSED"]}},
            {"_id": 0},
        ),
        fallback=None,
    ) or {}
    device = _ensure_patient_device(db, patient_id, patient)
    schedule_id = existing.get("schedule_id") or f"SCHED-{uuid.uuid4().hex[:8].upper()}"
    doc = {
        "schedule_id": schedule_id,
        "patient_id": patient_id,
        "patient_name": _display_value(patient.get("name")) or patient_id,
        "prescription_id": rx.get("prescription_id", ""),
        "medicine_name": rx.get("medicine_name", _split_medication_text(patient.get("medicine_name"))[0]),
        "strength": rx.get("strength", ""),
        "device_id": existing.get("device_id") or device.get("device_id", ""),
        "ward": patient.get("ward") or device.get("ward", ""),
        "scheduled_time": target_time,
        "target_time": target_time,
        "status": "PENDING",
        "date": today,
        "updated_at": _ist_now(),
        "scan_type": "IMAGE_BASELINE_THEN_VERIFY",
    }
    if not existing:
        doc["created_at"] = _ist_now()
    _safe_db_call(lambda: db["daily_schedule"].update_one({"schedule_id": schedule_id}, {"$set": doc}, upsert=True))
    return doc


def _sync_patient_ordering(db, patient_id: str, patient: Dict[str, Any], next_time: Any = None) -> Dict[str, Any]:
    med_text = _display_value(patient.get("medicine_name")) or _display_value(patient.get("medication"))
    rx = _upsert_patient_prescription(db, patient_id, patient, med_text)
    schedule = None
    if rx:
        schedule_time = next_time if next_time is not None else patient.get("next_dose")
        schedule = _upsert_patient_schedule(db, patient_id, patient, rx, schedule_time)
    return {"prescription": rx, "schedule": schedule}


def _sanitize(obj):
    """
    Recursively convert any non-JSON-serializable values in a dict/list
    to safe strings. Handles MongoDB ObjectId, datetime, bytes, etc.
    """
    from bson import ObjectId
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items() if k != "_id"}
    if isinstance(obj, list):
        return [_sanitize(i) for i in obj]
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    return obj


# ═══════════════════════════════════════════════════════════════════════════════
# ROOT & HEALTH  (unchanged)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/")
def root():
    """Root status endpoint."""
    return {
        "service": "Medicine Dispenser AI Subsystem API",
        "version": "2.0.0",
        "docs": "/docs",
    }


@app.get("/api/v1/health")
def health_check():
    """Service health and database ping endpoint."""
    res = _api_service().health()
    return res.to_dict()


# ═══════════════════════════════════════════════════════════════════════════════
# AI INSPECTION  (unchanged core endpoint)
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/devices/{device_id}/inspection")
async def inspect_device(
    device_id: str,
    file: Optional[UploadFile] = File(None),
    simulated_ocr_text: Optional[str] = Form(None),
    total_slots: Optional[int] = Form(10),
    missing_count: Optional[int] = Form(0),
):
    """
    IoT Camera Inspection Trigger Endpoint.
    Routes by device_id -> Patient -> Prescription, runs AI subsystems,
    and persists session in MongoDB.
    """
    image_array = None
    if file is not None:
        contents = await file.read()
        bytes_arr = np.frombuffer(contents, np.uint8)
        image_array = cv2.imdecode(bytes_arr, cv2.IMREAD_COLOR)

    # CRITICAL FIX: Only use raw_inspection fallback when NO real image is provided.
    # If a real image is uploaded, pass raw_inspection=None so the AI pipeline
    # (Models A→B→C) actually runs instead of returning hardcoded zeros.
    if image_array is not None:
        raw_inspection = None
    else:
        ts = total_slots if total_slots is not None else 10
        mc = missing_count if missing_count is not None else 0
        raw_inspection = {
            "total": ts,
            "present": max(0, ts - mc),
            "missing": mc,
            "missing_indices": list(range(1, mc + 1)) if mc > 0 else [],
        }

    res = _api_service().inspect_device(
        device_id=device_id,
        image_array=image_array,
        raw_inspection=raw_inspection,
        simulated_ocr_text=simulated_ocr_text,
    )

    if not res.success:
        raise HTTPException(status_code=res.status_code, detail=res.error_message)

    return _sanitize(res.to_dict())



# ═══════════════════════════════════════════════════════════════════════════════
# LEGACY PER-PATIENT API  (unchanged)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/patients/{patient_id}")
def get_patient_by_id(patient_id: str):
    """Retrieve patient demographic record."""
    patient = _patient_lookup(_db()).get(patient_id)
    if patient:
        return {"success": True, "data": patient}
    res = _api_service().get_patient(patient_id)
    if not res.success:
        raise HTTPException(status_code=res.status_code, detail=res.error_message)
    return res.to_dict()


@app.get("/api/v1/patients/{patient_id}/prescriptions")
def get_patient_prescriptions(patient_id: str):
    """Retrieve patient active prescriptions."""
    prescriptions = [
        rx for rx in _prescription_lookup(_db()).get(patient_id, [])
        if rx.get("active", True)
    ]
    if prescriptions:
        return {"success": True, "data": {"prescriptions": prescriptions}}
    res = _api_service().get_patient_prescriptions(patient_id)
    if not res.success or not res.to_dict().get("data", {}).get("prescriptions"):
        return {"success": True, "data": {"prescriptions": prescriptions}}
    return res.to_dict()


@app.get("/api/v1/patients/{patient_id}/schedule")
def get_patient_schedule(patient_id: str):
    """Retrieve patient daily dose schedule."""
    rows = _patient_schedule_rows(_db(), patient_id)
    if rows:
        return {"success": True, "data": {"schedules": rows}}
    res = _api_service().get_patient_schedule(patient_id)
    payload = res.to_dict()
    schedules = payload.get("data", {}).get("schedules", []) if isinstance(payload, dict) else []
    if not res.success or not schedules:
        return {"success": True, "data": {"schedules": rows}}
    return payload


@app.get("/api/v1/alerts/{patient_id}")
def get_patient_alerts(patient_id: str):
    """Retrieve patient alert history."""
    res = _api_service().get_alert_history(patient_id)
    return res.to_dict()


# ═══════════════════════════════════════════════════════════════════════════════
# FRONTEND: PATIENTS  /patients
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/patients")
def list_patients():
    """List all patients — used by Patients page."""
    db = _db()
    docs = _safe_db_call(lambda: _patients().list_all(), fallback=DEFAULT_PATIENTS)
    rx_by_patient = _prescription_lookup(db)
    schedules = _safe_db_call(lambda: _schedules().list_all(), fallback=[])

    schedule_by_patient: Dict[str, Dict[str, Any]] = {}
    for sched in schedules:
        pat_id = sched.get("patient_id", "")
        if not pat_id:
            continue
        current = schedule_by_patient.get(pat_id)
        if current is None or current.get("status") != "PENDING":
            schedule_by_patient[pat_id] = sched
    result = []
    for p in docs:
        pat_id = p.get("patient_id", "")
        rx = (rx_by_patient.get(pat_id) or [{}])[0]
        sched = schedule_by_patient.get(pat_id, {})
        medication = (
            _display_value(p.get("medicine_name"))
            or _display_value(p.get("medication"))
            or _display_value(rx.get("medicine_name"))
            or _display_value(sched.get("medicine_name"))
            or ""
        )
        next_dose = (
            _display_value(p.get("next_dose"))
            or _display_value(p.get("next"))
            or _display_value(sched.get("target_time"))
            or _display_value(sched.get("scheduled_time"))
            or "No Schedule"
        )
        result.append({
            "id":         pat_id,
            "name":       p.get("name", ""),
            "ward":       p.get("ward", ""),
            "medication": medication,
            "next":       next_dose,
            "status":     p.get("status", "Active"),
            "age":        p.get("age", ""),
            "gender":     p.get("gender", ""),
            "bedNumber":  p.get("bed_number", p.get("bedNumber", "")),
            "doctor":     p.get("doctor", ""),
            "caregiver":  p.get("caregiver_contact", ""),
        })
    return _sanitize(result)


@app.post("/patients")
def add_patient(body: Dict[str, Any] = Body(...)):
    """
    Add a new patient record and automatically:
      1. Create a linked IoT Device for them (DEV-{name_slug})
      2. Create an active Prescription for their medication
      3. Create a Daily Schedule only when a real next-dose time is provided
    """
    repo = _patients()
    raw_name = body.get("name", "Unknown").strip()
    name_slug = "".join([c.upper() for c in raw_name if c.isalnum()])[:8] or uuid.uuid4().hex[:6].upper()
    new_id = f"PAT-{name_slug}"
    
    # Check if ID already exists, append random suffix if needed
    existing = _safe_db_call(lambda: repo.find_by_id(new_id))
    if existing:
        new_id = f"PAT-{name_slug}-{uuid.uuid4().hex[:4].upper()}"

    med_input = body.get("medication", "Paracetamol 500mg").strip()
    parts = med_input.split()
    if len(parts) > 1 and any(unit in parts[-1].lower() for unit in ["mg", "mcg", "g", "ml"]):
        strength = parts[-1]
        brand = " ".join(parts[:-1])
    else:
        brand = med_input
        strength = "500mg"

    next_time = _display_value(body.get("next"))
    minutes_raw = body.get("minutesFromNow")
    if minutes_raw not in (None, ""):
        try:
            minutes_from_now = max(1, min(1440, int(minutes_raw)))
            next_time = (datetime.now(timezone(timedelta(hours=5, minutes=30))) + timedelta(minutes=minutes_from_now)).strftime("%H:%M")
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="minutesFromNow must be a number")
    if not next_time or ":" not in next_time or next_time == "—":
        next_time = ""

    doc = {
        "patient_id":        new_id,
        "name":              raw_name,
        "ward":              body.get("ward", "Ward 1"),
        "medicine_name":     med_input,
        "next_dose":         next_time,
        "status":            body.get("status", "Active"),
        "age":               int(body.get("age", 0)) if str(body.get("age", "")).isdigit() else body.get("age", 0),
        "gender":            body.get("gender", "Other"),
        "bed_number":        body.get("bedNumber", "Bed 1"),
        "doctor":            body.get("doctor", "Dr. Primary"),
        "caregiver_contact": body.get("caregiver", "+91-98765-00000"),
        "created_at":        _ist_now(),
    }
    _safe_db_call(lambda: repo.insert_one(doc))

    # 1. Auto-create linked Device
    dev_id = _display_value(body.get("deviceId") or body.get("device_id")) or f"DEV-{name_slug}"
    dev_doc = {
        "device_id":     dev_id,
        "patient_id":    new_id,
        "ward":          doc["ward"],
        "room":          doc["bed_number"],
        "status":        "Online",
        "battery_level": 98,
        "slots_used":    0,
        "slots_total":   10,
        "camera_id":     f"CAM-{name_slug[-4:]}",
        "last_seen":     "Just now",
        "created_at":    _ist_now(),
    }
    _safe_db_call(lambda: _devices().collection.update_one(
        {"device_id": dev_id},
        {"$set": dev_doc},
        upsert=True
    ))

    # 2. Auto-create active Prescription
    rx_id = f"RX-{name_slug}"
    rx_doc = {
        "prescription_id": rx_id,
        "patient_id":      new_id,
        "patient_name":    raw_name,
        "medicine_name":   brand,
        "strength":        strength,
        "dosage_form":     "Tablet",
        "doses_per_day":   1,
        "frequency":       "Once daily",
        "start_date":      _ist_now().split("T")[0],
        "end_date":        "2026-12-31",
        "doctor":          doc["doctor"],
        "active":          True,
        "created_at":      _ist_now(),
    }
    _safe_db_call(lambda: _prescriptions().collection.update_one(
        {"prescription_id": rx_id},
        {"$set": rx_doc},
        upsert=True
    ))

    if next_time:
        sched_id = f"SCHED-{name_slug}"
        sched_doc = {
            "schedule_id":     sched_id,
            "patient_id":      new_id,
            "patient_name":    raw_name,
            "prescription_id": rx_id,
            "medicine_name":   brand,
            "strength":        strength,
            "device_id":       dev_id,
            "scheduled_time":  next_time,
            "target_time":     next_time,
            "status":          "PENDING",
            "date":            _ist_now().split("T")[0],
            "scan_type":       "IMAGE_BASELINE_THEN_VERIFY",
        }
        _safe_db_call(lambda: _schedules().collection.update_one(
            {"schedule_id": sched_id},
            {"$set": sched_doc},
            upsert=True
        ))

    doc["id"] = new_id
    doc["device_id"] = dev_id
    message = "Patient added & device/prescription linked"
    if next_time:
        message += " with schedule"
    return _sanitize({"message": message, "data": doc})


@app.put("/patients/{patient_id}")
def update_patient(patient_id: str, body: Dict[str, Any] = Body(...)):
    """Update an existing patient record."""
    repo = _patients()
    current = _safe_db_call(lambda: repo.find_by_id(patient_id), fallback={}) or {}
    updates = {}
    if "name" in body:         updates["name"] = body["name"]
    if "ward" in body:         updates["ward"] = body["ward"]
    if "medication" in body:   updates["medicine_name"] = body["medication"]
    if "next" in body:         updates["next_dose"] = body["next"]
    if "status" in body:       updates["status"] = body["status"]
    if "age" in body:          updates["age"] = body["age"]
    if "gender" in body:       updates["gender"] = body["gender"]
    if "bedNumber" in body:    updates["bed_number"] = body["bedNumber"]
    if "doctor" in body:       updates["doctor"] = body["doctor"]
    if "caregiver" in body:    updates["caregiver_contact"] = body["caregiver"]
    _safe_db_call(lambda: repo.collection.update_one({"patient_id": patient_id}, {"$set": updates}))
    
    # Also sync ward/room to device if updated
    if "ward" in body or "bedNumber" in body:
        dev_up = {}
        if "ward" in body: dev_up["ward"] = body["ward"]
        if "bedNumber" in body: dev_up["room"] = body["bedNumber"]
        _safe_db_call(lambda: _devices().collection.update_many({"patient_id": patient_id}, {"$set": dev_up}))

    merged_patient = dict(current)
    merged_patient.update(updates)
    sync_result = _sync_patient_ordering(_db(), patient_id, merged_patient, body.get("next"))

    updates["id"] = patient_id
    if sync_result.get("prescription"):
        updates["prescriptionId"] = sync_result["prescription"].get("prescription_id")
    if sync_result.get("schedule"):
        updates["scheduleId"] = sync_result["schedule"].get("schedule_id")
    return _sanitize({"message": "Patient updated", "data": updates})


@app.delete("/patients/{patient_id}")
def delete_patient(patient_id: str):
    """Delete a patient and every workflow record linked to that patient."""
    db = _db()
    linked_devices = _safe_db_call(
        lambda: list(db["devices"].find({"patient_id": patient_id}, {"_id": 0, "device_id": 1})),
        fallback=[],
    )
    device_ids = [d.get("device_id") for d in linked_devices if d.get("device_id")]

    cascade = {
        "patients": {"patient_id": patient_id},
        "devices": {"patient_id": patient_id},
        "prescriptions": {"patient_id": patient_id},
        "daily_schedule": {"patient_id": patient_id},
        "scan_baselines": {"patient_id": patient_id},
        "inspection_sessions": {"patient_id": patient_id},
        "inspection_results": {"patient_id": patient_id},
        "clinical_decisions": {"patient_id": patient_id},
        "compliance_decisions": {"patient_id": patient_id},
        "alerts": {"patient_id": patient_id},
    }
    for collection_name, query in cascade.items():
        _safe_db_call(lambda name=collection_name, q=query: db[name].delete_many(q))

    for device_id in device_ids:
        _safe_db_call(lambda did=device_id: db["scan_baselines"].delete_many({"device_id": did}))
        _safe_db_call(lambda did=device_id: db["inspection_sessions"].delete_many({"device_id": did}))
        _safe_db_call(lambda did=device_id: db["alerts"].delete_many({"device_id": did}))

    return _sanitize({"message": "Patient and linked workflow records deleted", "data": {"patientId": patient_id, "deviceIds": device_ids}})



# ═══════════════════════════════════════════════════════════════════════════════
# FRONTEND: MEDICATIONS  /medications
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/medications")
def list_medications():
    """List all medications from medicine_catalogue — used by Medications page."""
    docs = _safe_db_call(lambda: _meds().list_all(), fallback=DEFAULT_MEDS)
    result = []
    for m in docs:
        stock = m.get("current_stock", m.get("stock", 0))
        threshold = m.get("low_stock_threshold", m.get("threshold", 10))
        if stock <= threshold // 2:
            status = "Critical"
        elif stock <= threshold:
            status = "Low Stock"
        else:
            status = "OK"
        result.append({
            "id":        m.get("medicine_id", m.get("id", "")),
            "name":      m.get("brand", m.get("name", "")),
            "dosage":    m.get("strength", m.get("dosage", "")),
            "stock":     stock,
            "threshold": threshold,
            "expiry":    m.get("expiry_date", m.get("expiry", "")),
            "status":    status,
        })
    return _sanitize(result)


@app.post("/medications")
def add_medication(body: Dict[str, Any] = Body(...)):
    """Add a new medication to catalogue."""
    repo = _meds()
    new_id = f"MED-{uuid.uuid4().hex[:6].upper()}"
    doc = {
        "medicine_id":         new_id,
        "brand":               body.get("name", ""),
        "strength":            body.get("dosage", ""),
        "current_stock":       int(body.get("stock", 0)),
        "low_stock_threshold": int(body.get("threshold", 10)),
        "expiry_date":         body.get("expiry", ""),
        "ocr_aliases":         [body.get("name", "").lower()],
    }
    _safe_db_call(lambda: repo.insert_one(doc))
    doc["id"] = new_id
    return _sanitize({"message": "Medication added", "data": doc})


@app.put("/medications/{med_id}")
def update_medication(med_id: str, body: Dict[str, Any] = Body(...)):
    """Update a medication record."""
    repo = _meds()
    updates = {}
    if "name" in body:      updates["brand"] = body["name"]
    if "dosage" in body:    updates["strength"] = body["dosage"]
    if "stock" in body:     updates["current_stock"] = int(body["stock"])
    if "threshold" in body: updates["low_stock_threshold"] = int(body["threshold"])
    if "expiry" in body:    updates["expiry_date"] = body["expiry"]
    _safe_db_call(lambda: repo.collection.update_one({"medicine_id": med_id}, {"$set": updates}))
    updates["id"] = med_id
    return _sanitize({"message": "Medication updated", "data": updates})


@app.delete("/medications/{med_id}")
def delete_medication(med_id: str):
    """Delete a medication from catalogue."""
    repo = _meds()
    _safe_db_call(lambda: repo.collection.delete_one({"medicine_id": med_id}))
    return {"message": "Medication deleted"}


# ═══════════════════════════════════════════════════════════════════════════════
# FRONTEND: DEVICES  /devices
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/devices")
def list_devices():
    """List all devices enriched with patient name & medication for clear selection."""
    db = _db()
    docs = _safe_db_call(lambda: _devices().list_all(), fallback=DEFAULT_DEVICES)
    patients_map = _patient_lookup(db)
    prescriptions_map = _prescription_lookup(db)

    known = list(DEFAULT_DEVICES) + list(docs or [])
    linked_patient_ids = {d.get("patient_id") for d in known if d.get("patient_id")}
    for pid, patient_doc in patients_map.items():
        if pid and pid not in linked_patient_ids:
            repaired = _ensure_patient_device(db, pid, patient_doc)
            docs.append(repaired)
            linked_patient_ids.add(pid)

    result = []
    for d in docs:
        pid = d.get("patient_id", "")
        if pid and pid not in patients_map:
            continue
        p_info = patients_map.get(pid, {})
        rx_info = (prescriptions_map.get(pid) or [{}])[0]
        p_name = p_info.get("name") or pid or "Unassigned"
        p_med = rx_info.get("medicine_name") or p_info.get("medicine_name", "")
        p_ward = d.get("ward") or p_info.get("ward", "")

        result.append({
            "id":            d.get("device_id", ""),
            "device_id":     d.get("device_id", ""),
            "ward":          p_ward,
            "room":          d.get("room", d.get("location", p_info.get("bed_number", ""))),
            "status":        d.get("status", "Online"),
            "battery":       d.get("battery_level", d.get("battery", 100)),
            "slotsUsed":     d.get("slots_used", d.get("slotsUsed", 0)),
            "slotsTotal":    d.get("slots_total", d.get("slotsTotal", 10)),
            "lastHeartbeat": d.get("last_seen", d.get("lastHeartbeat", "")),
            "patientId":     pid,
            "patient_id":    pid,
            "patientName":   p_name,
            "medication":    p_med,
            "cameraId":      d.get("camera_id", ""),
        })
    return _sanitize(result)


@app.post("/devices")
def register_device(body: Dict[str, Any] = Body(...)):
    """Register a new IoT device."""
    repo = _devices()
    new_id = body.get("id") or body.get("device_id") or f"DEV-{uuid.uuid4().hex[:8].upper()}"
    doc = {
        "device_id":     new_id,
        "ward":          body.get("ward", ""),
        "room":          body.get("room", ""),
        "status":        body.get("status", "Online"),
        "battery_level": int(body.get("battery", 100)),
        "slots_used":    int(body.get("slotsUsed", 0)),
        "slots_total":   int(body.get("slotsTotal", 10)),
        "patient_id":    body.get("patientId", ""),
        "camera_id":     body.get("cameraId", ""),
        "last_seen":     "Just now",
        "created_at":    _ist_now(),
    }
    _safe_db_call(lambda: repo.insert_one(doc))
    doc["id"] = new_id
    return _sanitize({"message": "Device registered", "data": doc})


@app.patch("/devices/{device_id}")
@app.put("/devices/{device_id}")
def update_device(device_id: str, body: Dict[str, Any] = Body(...)):
    """Update device fields (status, battery, slots, restart)."""
    repo = _devices()
    updates = {}
    if "status" in body:        updates["status"] = body["status"]
    if "battery" in body:       updates["battery_level"] = int(body["battery"])
    if "slotsUsed" in body:     updates["slots_used"] = int(body["slotsUsed"])
    if "slotsTotal" in body:    updates["slots_total"] = int(body["slotsTotal"])
    if "ward" in body:          updates["ward"] = body["ward"]
    if "room" in body:          updates["room"] = body["room"]
    if "patientId" in body:     updates["patient_id"] = body["patientId"]
    if "lastHeartbeat" in body: updates["last_seen"] = body["lastHeartbeat"]
    _safe_db_call(lambda: repo.collection.update_one({"device_id": device_id}, {"$set": updates}))
    updates["id"] = device_id
    return _sanitize({"message": "Device updated", "data": updates})


@app.patch("/devices/{device_id}/restart")
def restart_device(device_id: str):
    """Set device status to Restarting."""
    repo = _devices()
    _safe_db_call(lambda: repo.collection.update_one({"device_id": device_id}, {"$set": {"status": "Restarting"}}))
    return {"message": "Device restarting"}


@app.delete("/devices/{device_id}")
def delete_device(device_id: str):
    """Delete a device record."""
    repo = _devices()
    _safe_db_call(lambda: repo.collection.delete_one({"device_id": device_id}))
    return {"message": "Device deleted"}


# ═══════════════════════════════════════════════════════════════════════════════
# FRONTEND: ALERTS  /alerts
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/alerts")
def list_all_alerts(type: Optional[str] = None, status: Optional[str] = None):
    """List all alerts across all patients — used by Alerts page."""
    db = _db()
    _safe_db_call(lambda: _check_and_update_missed_schedules(db))
    query: Dict[str, Any] = {}
    if type:
        query["type"] = type
    if status:
        query["status"] = status
    
    docs = _safe_db_call(lambda: list(db["alerts"].find(query, {"_id": 0})), fallback=DEFAULT_ALERTS)
    patients = _patient_lookup(db)
    devices = _device_lookup(db)

    result = []
    for a in docs:
        pat_id = a.get("patient_id", a.get("patientId", ""))
        patient_doc = patients.get(pat_id, {})
        device_doc = _device_for_patient(pat_id, devices)
        pat_name = a.get("patient") or ((patient_doc.get("name") if isinstance(patient_doc, dict) else pat_id) or "—")
        ward_name = a.get("ward") or ((patient_doc.get("ward") if isinstance(patient_doc, dict) else "—") or "—")
        dev_id = a.get("device") or a.get("device_id") or "—"

        pat_name = a.get("patient") or _patient_name(pat_id, patients)
        ward_name = a.get("ward") or _patient_ward(pat_id, patients, device_doc.get("ward", ""))
        dev_id = a.get("device") or a.get("device_id") or device_doc.get("device_id") or "-"

        alt_type = a.get("type")
        if not alt_type or alt_type not in ["Medication", "Device"]:
            alt_type = "Medication"

        st = a.get("status", "Active")
        sev = str(a.get("severity", "")).upper()
        if sev == "CRITICAL" and st == "Active":
            st = "Critical"
        elif sev == "WARNING" and st == "Active":
            st = "Warning"

        raw_ts = a.get("timestamp", "")
        time_str = a.get("time") or ""
        if not time_str and raw_ts:
            try:
                time_str = raw_ts.split("T")[1][:8] if "T" in raw_ts else raw_ts[:8]
            except Exception:
                time_str = raw_ts

        desc_str = a.get("desc") or a.get("description") or a.get("message") or a.get("title") or "—"

        result.append({
            "id":           a.get("alert_id", a.get("id", "")),
            "patientId":    pat_id,
            "patient":      pat_name,
            "device":       dev_id,
            "ward":         ward_name,
            "type":         alt_type,
            "desc":         desc_str,
            "message":      a.get("message", desc_str),
            "title":        a.get("title", desc_str),
            "time":         time_str,
            "timestamp":    raw_ts,
            "status":       st,
            "channel":      a.get("channel", ""),
            "recipient":    a.get("recipient", ""),
            "acknowledged": a.get("acknowledged", False),
        })
    result.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return _sanitize(result)


@app.patch("/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: str):
    """Mark an alert as resolved."""
    db = _db()
    _safe_db_call(lambda: db["alerts"].update_one(
        {"alert_id": alert_id},
        {"$set": {"status": "Resolved", "acknowledged": True, "resolvedAt": _ist_now()}}
    ))
    return {"message": "Alert resolved"}


@app.delete("/alerts/{alert_id}")
def delete_alert(alert_id: str):
    """Delete/dismiss an alert."""
    db = _db()
    _safe_db_call(lambda: db["alerts"].delete_one({"alert_id": alert_id}))
    return {"message": "Alert deleted"}


# ═══════════════════════════════════════════════════════════════════════════════
# FRONTEND: PRESCRIPTIONS  /prescriptions
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/prescriptions")
def list_prescriptions():
    """List all prescriptions — used by Prescriptions page."""
    db = _db()
    docs = _safe_db_call(lambda: _prescriptions().list_all(), fallback=DEFAULT_PRESCRIPTIONS)
    patients = _patient_lookup(db)
    result = []
    for p in docs:
        pat_id = p.get("patient_id", "")
        result.append({
            "id":          p.get("prescription_id", ""),
            "patientId":   pat_id,
            "patientName": p.get("patient_name") or _patient_name(pat_id, patients),
            "medication":  p.get("medicine_name", p.get("medication", "")),
            "dosage":      p.get("strength", p.get("dosage", "")),
            "frequency":   p.get("frequency", ""),
            "startDate":   p.get("start_date", p.get("startDate", "")),
            "endDate":     p.get("end_date", p.get("endDate", "")),
            "doctor":      p.get("doctor", ""),
            "status":      "Active" if p.get("active", True) else "Inactive",
        })
    return _sanitize(result)


@app.post("/prescriptions")
def add_prescription(body: Dict[str, Any] = Body(...)):
    """Add a new prescription."""
    db = _db()
    patient_id = body.get("patientId") or body.get("patient_id")
    medication = _display_value(body.get("medication") or body.get("medicine_name"))
    if not patient_id:
        raise HTTPException(status_code=400, detail="patientId is required")
    if not medication:
        raise HTTPException(status_code=400, detail="medication is required")

    patients = _patient_lookup(db)
    patient = patients.get(patient_id, {"patient_id": patient_id})
    patient_name = _display_value(body.get("patientName")) or _display_value(patient.get("name")) or patient_id
    dosage = _display_value(body.get("dosage") or body.get("strength"))
    if not dosage:
        medication, dosage = _split_medication_text(medication)

    new_id = f"RX-{uuid.uuid4().hex[:8].upper()}"
    doc = {
        "prescription_id": new_id,
        "patient_id":      patient_id,
        "patient_name":    patient_name,
        "medicine_name":   medication,
        "strength":        dosage,
        "dosage_form":     "Tablet",
        "doses_per_day":   1,
        "frequency":       body.get("frequency", "Once daily"),
        "start_date":      body.get("startDate") or _ist_now().split("T")[0],
        "end_date":        body.get("endDate", ""),
        "doctor":          body.get("doctor", patient.get("doctor", "")),
        "active":          True,
        "created_at":      _ist_now(),
    }
    _safe_db_call(lambda: db["prescriptions"].insert_one(doc))
    _safe_db_call(lambda: db["patients"].update_one(
        {"patient_id": patient_id},
        {"$set": {"medicine_name": f"{medication} {dosage}".strip()}},
    ))
    doc["id"] = new_id
    return _sanitize({"message": "Prescription added", "data": doc})


@app.put("/prescriptions/{rx_id}")
def update_prescription(rx_id: str, body: Dict[str, Any] = Body(...)):
    """Update a prescription record."""
    repo = _prescriptions()
    current = _safe_db_call(lambda: repo.find_by_id(rx_id), fallback={}) or {}
    updates = {}
    if "medication" in body: updates["medicine_name"] = body["medication"]
    if "dosage" in body:     updates["strength"] = body["dosage"]
    if "frequency" in body:  updates["frequency"] = body["frequency"]
    if "startDate" in body:  updates["start_date"] = body["startDate"]
    if "endDate" in body:    updates["end_date"] = body["endDate"]
    if "doctor" in body:     updates["doctor"] = body["doctor"]
    if "status" in body:     updates["active"] = body["status"] == "Active"
    _safe_db_call(lambda: repo.collection.update_one({"prescription_id": rx_id}, {"$set": updates}))
    merged = dict(current)
    merged.update(updates)
    patient_id = merged.get("patient_id", "")
    if patient_id and ("medicine_name" in updates or "strength" in updates):
        med_text = f"{merged.get('medicine_name', '')} {merged.get('strength', '')}".strip()
        _safe_db_call(lambda: _db()["patients"].update_one({"patient_id": patient_id}, {"$set": {"medicine_name": med_text}}))
        _safe_db_call(lambda: _db()["daily_schedule"].update_many(
            {"patient_id": patient_id, "prescription_id": rx_id, "status": {"$in": ["PENDING", "MISSED"]}},
            {"$set": {
                "medicine_name": merged.get("medicine_name", ""),
                "strength": merged.get("strength", ""),
                "updated_at": _ist_now(),
            }},
        ))
    updates["id"] = rx_id
    return _sanitize({"message": "Prescription updated", "data": updates})


@app.delete("/prescriptions/{rx_id}")
def delete_prescription(rx_id: str):
    """Delete a prescription."""
    repo = _prescriptions()
    _safe_db_call(lambda: repo.collection.delete_one({"prescription_id": rx_id}))
    return {"message": "Prescription deleted"}


# ═══════════════════════════════════════════════════════════════════════════════
# FRONTEND: SCHEDULES  /schedules
# ═══════════════════════════════════════════════════════════════════════════════

def _check_and_update_missed_schedules(db):
    """
    Check all PENDING daily_schedule entries for every patient.
    If current IST time > target_time + 5 minutes grace window AND no scan was performed,
    mark the schedule as 'MISSED - NOT SCANNED' and dispatch a clinical alert to MongoDB.
    """
    try:
        ist_tz = timezone(timedelta(hours=5, minutes=30))
        now_ist = datetime.now(ist_tz)

        pending_schedules = list(db["daily_schedule"].find({"status": "PENDING"}))
        for sched in pending_schedules:
            t_str = sched.get("target_time", "")
            if not t_str or ":" not in t_str:
                continue

            try:
                hh, mm = map(int, t_str.split(":"))
                sched_dt = now_ist.replace(hour=hh, minute=mm, second=0, microsecond=0)
                diff_minutes = (now_ist - sched_dt).total_seconds() / 60.0

                if 5.0 <= diff_minutes <= 1080.0:
                    sched_id = sched["schedule_id"]
                    pat_id = sched.get("patient_id", "")
                    med_name = sched.get("medicine_name", "Medicine")
                    strength = sched.get("strength", "")
                    dev_id = sched.get("device_id", "")

                    patient_doc = db["patients"].find_one({"patient_id": pat_id}) if pat_id else None
                    pat_name = patient_doc.get("name", pat_id) if patient_doc else pat_id
                    ward = patient_doc.get("ward", "Ward A") if patient_doc else "Ward A"

                    db["daily_schedule"].update_one(
                        {"schedule_id": sched_id},
                        {"$set": {
                            "status": "MISSED",
                            "missed_at": now_ist.isoformat(),
                            "missed_reason": f"No scan submitted within 5 min of {t_str} scheduled dose.",
                        }}
                    )

                    existing_alert = db["alerts"].find_one({"schedule_id": sched_id})
                    if not existing_alert:
                        alert_id = f"alt_miss_{uuid.uuid4().hex[:8]}"
                        desc_msg = f"Dose Missed: {med_name} ({strength}) scheduled at {t_str} was NOT scanned by patient."
                        db["alerts"].insert_one({
                            "alert_id":     alert_id,
                            "schedule_id":  sched_id,
                            "patient_id":   pat_id,
                            "patient":      f"{pat_name} ({pat_id})",
                            "device":       dev_id or "—",
                            "device_id":    dev_id or "—",
                            "ward":         ward,
                            "room":         patient_doc.get("room", "Room 1") if patient_doc else "Room 1",
                            "type":         "Medication",
                            "severity":     "WARNING",
                            "status":       "Warning",
                            "title":        f"Dose Missed: {med_name} {strength}",
                            "message":      desc_msg,
                            "desc":         desc_msg,
                            "description":  desc_msg,
                            "recipient":    f"Assigned Caregiver of {pat_name}",
                            "channel":      "CAREGIVER_ALERT",
                            "time":         now_ist.strftime("%H:%M:%S"),
                            "timestamp":    now_ist.isoformat(),
                            "acknowledged": False,
                        })
            except Exception:
                pass
    except Exception:
        pass


@app.get("/schedules")
def list_schedules():
    """List all dose schedules — automatically updates missed schedules if time has elapsed."""
    db = _db()
    _safe_db_call(lambda: _check_and_update_missed_schedules(db))
    docs = _safe_db_call(lambda: _schedules().list_all(), fallback=[])
    patients = _patient_lookup(db)
    devices = _device_lookup(db)
    result = []
    for s in docs:
        pat_id = s.get("patient_id", "")
        dev_id = s.get("device_id", s.get("deviceId", ""))
        device_doc = devices.get(dev_id, {}) if dev_id else _device_for_patient(pat_id, devices)
        patient_doc = _safe_db_call(lambda: db["patients"].find_one({"patient_id": pat_id}, {"_id": 0}), fallback={}) if pat_id else {}
        pat_name = s.get("patient_name") or ((patient_doc.get("name") if isinstance(patient_doc, dict) else pat_id) or "—")

        result.append({
            "id":             s.get("schedule_id", ""),
            "patient":        s.get("patient_name") or _patient_name(pat_id, patients),
            "patientId":      pat_id,
            "prescriptionId": s.get("prescription_id", ""),
            "medication":     s.get("medicine_name", s.get("medication", "")),
            "deviceId":       dev_id or device_doc.get("device_id", ""),
            "ward":           s.get("ward") or _patient_ward(pat_id, patients, device_doc.get("ward", "")),
            "time":           s.get("target_time", s.get("scheduled_time", s.get("time", ""))),
            "status":         s.get("status", "Pending"),
        })
    return _sanitize(result)


@app.post("/schedules")
def add_schedule(body: Dict[str, Any] = Body(...)):
    """Create a patient image-scan schedule, with quick minute offsets for testing."""
    db = _db()
    patient_id = body.get("patientId") or body.get("patient_id")
    if not patient_id:
        raise HTTPException(status_code=400, detail="patientId is required")

    patients = _patient_lookup(db)
    patient = patients.get(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found")

    rx_list = [
        item for item in _prescription_lookup(db).get(patient_id, [])
        if item.get("active", True)
    ]
    requested_rx_id = body.get("prescriptionId") or body.get("prescription_id")
    rx = None
    if requested_rx_id:
        rx = next((item for item in rx_list if item.get("prescription_id") == requested_rx_id), None)
    if rx is None and rx_list:
        rx = rx_list[0]
    if rx is None:
        patient_med = _display_value(patient.get("medicine_name")) or _display_value(patient.get("medication"))
        rx = _upsert_patient_prescription(db, patient_id, patient, patient_med)
    if rx is None:
        raise HTTPException(status_code=400, detail="Add medication or an active prescription before scheduling an image scan")

    devices = _device_lookup(db)
    requested_device_id = body.get("deviceId") or body.get("device_id")
    device = devices.get(requested_device_id, {}) if requested_device_id else _device_for_patient(patient_id, devices)
    if not device:
        device = _ensure_patient_device(db, patient_id, patient, requested_device_id)

    now_ist = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    minutes_raw = body.get("minutesFromNow")
    if minutes_raw not in (None, ""):
        try:
            minutes_from_now = max(1, min(1440, int(minutes_raw)))
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="minutesFromNow must be a number")
        target_dt = now_ist + timedelta(minutes=minutes_from_now)
        target_time = target_dt.strftime("%H:%M")
    else:
        target_time = str(body.get("time") or body.get("target_time") or "").strip()

    if ":" not in target_time:
        raise HTTPException(status_code=400, detail="Schedule time must be HH:MM or use minutesFromNow")

    schedule_id = f"SCHED-{uuid.uuid4().hex[:8].upper()}"
    schedule_doc = {
        "schedule_id":     schedule_id,
        "patient_id":      patient_id,
        "patient_name":    patient.get("name", patient_id),
        "prescription_id": rx.get("prescription_id", ""),
        "medicine_name":   rx.get("medicine_name", patient.get("medicine_name", "")),
        "strength":        rx.get("strength", ""),
        "device_id":       requested_device_id or device.get("device_id", ""),
        "ward":            patient.get("ward") or device.get("ward", ""),
        "scheduled_time":  target_time,
        "target_time":     target_time,
        "status":          "PENDING",
        "date":            now_ist.date().isoformat(),
        "created_at":      now_ist.isoformat(),
        "scan_type":       "IMAGE_BASELINE_THEN_VERIFY",
    }
    _safe_db_call(lambda: _schedules().insert_one(schedule_doc))

    return _sanitize({
        "message": "Schedule created",
        "data": {
            "id": schedule_id,
            "patient": schedule_doc["patient_name"],
            "patientId": patient_id,
            "prescriptionId": schedule_doc["prescription_id"],
            "medication": schedule_doc["medicine_name"],
            "deviceId": schedule_doc["device_id"],
            "ward": schedule_doc["ward"],
            "time": target_time,
            "status": "PENDING",
        },
    })


@app.post("/schedules/check-missed")
def check_missed_schedules_endpoint():
    """Explicit endpoint to evaluate and update missed dose scans across all patients."""
    db = _db()
    _safe_db_call(lambda: _check_and_update_missed_schedules(db))
    return {"message": "Missed schedules evaluated and updated across all patients"}


@app.put("/schedules/{schedule_id}")
def update_schedule(schedule_id: str, body: Dict[str, Any] = Body(...)):
    """Update a schedule status."""
    repo = _schedules()
    updates = {}
    if "status" in body: updates["status"] = body["status"]
    if "time" in body:   updates["target_time"] = body["time"]
    _safe_db_call(lambda: repo.collection.update_one({"schedule_id": schedule_id}, {"$set": updates}))
    return {"message": "Schedule updated"}


# ═══════════════════════════════════════════════════════════════════════════════
# FRONTEND: AUDIT LOGS  /audits
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/audits")
def list_audits():
    """
    Return inspection sessions as audit log entries.
    InspectionRepository's inspection_sessions collection is our audit trail.
    """
    db = _db()
    docs = _safe_db_call(lambda: list(db["inspection_sessions"].find({}, {"_id": 0}).sort("timestamp", -1).limit(200)), fallback=[])
    patients = _patient_lookup(db)
    result = []
    for idx, d in enumerate(docs):
        patient_id = d.get("patient_id", "")
        patient_name = d.get("patient_name") or _patient_name(patient_id, patients)
        result.append({
            "id":        d.get("session_id", f"AUD-{idx:04d}"),
            "timestamp": d.get("timestamp", ""),
            "user":      f"Device {d.get('device_id', '')}",
            "patient":   patient_name,
            "module":    "AI Inspection Pipeline",
            "action":    f"Dose inspection for {patient_name}",
            "result":    d.get("status", d.get("compliance_outcome", "COMPLETED")),
            "status":    d.get("status", "COMPLETED"),
        })
    return _sanitize(result)


# ═══════════════════════════════════════════════════════════════════════════════
# FRONTEND: REPORTS  /reports
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/reports")
def list_reports():
    """Return reports list."""
    return _sanitize(_reports_store or [
        {"id": "REP-001", "type": "Daily Compliance", "generatedAt": _ist_now(), "status": "Ready", "format": "PDF"},
        {"id": "REP-002", "type": "Medication Usage",  "generatedAt": _ist_now(), "status": "Ready", "format": "CSV"},
        {"id": "REP-003", "type": "Device Status",     "generatedAt": _ist_now(), "status": "Ready", "format": "PDF"},
        {"id": "REP-004", "type": "Alert Summary",     "generatedAt": _ist_now(), "status": "Ready", "format": "PDF"},
    ])


@app.post("/reports/generate")
def generate_report(body: Dict[str, Any] = Body(...)):
    """Generate a new report entry."""
    report_type = body.get("type", "Custom Report")
    new_report = {
        "id":          f"REP-{uuid.uuid4().hex[:6].upper()}",
        "type":        report_type,
        "generatedAt": _ist_now(),
        "status":      "Ready",
        "format":      body.get("format", "PDF"),
    }
    _reports_store.append(new_report)
    return _sanitize({"message": "Report generated", "data": new_report})


# ═══════════════════════════════════════════════════════════════════════════════
# FRONTEND: SETTINGS  /settings
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/settings")
def get_settings():
    """Return system settings."""
    return _sanitize(_settings_store)


@app.put("/settings")
def update_settings(body: Dict[str, Any] = Body(...)):
    """Update system settings."""
    _settings_store.update(body)
    return _sanitize({"message": "Settings updated", "data": _settings_store})


# ═══════════════════════════════════════════════════════════════════════════════
# FRONTEND: DISPENSE MONITOR  /dispense
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/dispense")
def list_dispense_jobs():
    """
    Return clinical decisions as dispense jobs — used by DispensingMonitor page.
    Maps compliance decisions to the dispense job shape the frontend expects.
    """
    db = _db()
    docs = _safe_db_call(lambda: list(db["clinical_decisions"].find({}, {"_id": 0}).sort("timestamp", -1).limit(100)), fallback=[])
    patients = _patient_lookup(db)
    devices = _device_lookup(db)
    prescriptions = _prescription_lookup(db)
    result = []
    for d in docs:
        patient_id = d.get("patient_id", "")
        device_doc = _device_for_patient(patient_id, devices)
        rx = (prescriptions.get(patient_id) or [{}])[0]
        outcome = d.get("outcome", "PENDING")
        status_map = {
            "CORRECT_DOSE":  "Completed",
            "EXTRA_DOSE":    "Warning",
            "DOSE_MISSED":   "Missed",
            "WRONG_MEDICINE":"Error",
            "EXPIRED_MEDICINE": "Error",
            "PENDING":       "Pending",
        }
        result.append({
            "id":         d.get("decision_id", ""),
            "patient":    _patient_name(patient_id, patients),
            "patientId":  patient_id,
            "medication": rx.get("medicine_name") or d.get("medicine_name") or d.get("reason", "")[:40],
            "device":     d.get("device_id") or device_doc.get("device_id", ""),
            "ward":       d.get("ward") or _patient_ward(patient_id, patients, device_doc.get("ward", "")),
            "time":       _time_value(d.get("timestamp", "")),
            "status":     status_map.get(outcome, "Pending"),
        })
    return _sanitize(result)


# ═══════════════════════════════════════════════════════════════════════════════
# FRONTEND: VERIFICATION QUEUE  /verifications
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/verifications")
def list_verifications():
    """
    Return pending/upcoming schedule entries as verification queue items.
    Used by VerificationQueue page.
    """
    db = _db()
    _safe_db_call(lambda: _check_and_update_missed_schedules(db))
    docs = _safe_db_call(lambda: _schedules().list_all(), fallback=[])
    patients = _patient_lookup(db)
    devices = _device_lookup(db)
    result = []
    for s in docs:
        status = s.get("status", "Pending")
        if status in ("Pending", "PENDING", "Missed", "MISSED"):
            patient_id = s.get("patient_id", "")
            dev_id = s.get("device_id", s.get("deviceId", ""))
            device_doc = devices.get(dev_id, {}) if dev_id else _device_for_patient(patient_id, devices)
            priority = "High" if status in ("Missed", "MISSED") else "Normal"
            result.append({
                "id":            s.get("schedule_id", ""),
                "patient":       s.get("patient_name") or s.get("patient") or _patient_name(patient_id, patients),
                "patientId":     patient_id,
                "medication":    s.get("medicine_name", s.get("medication", "")),
                "deviceId":      dev_id or device_doc.get("device_id", ""),
                "ward":          s.get("ward") or _patient_ward(patient_id, patients, device_doc.get("ward", "")),
                "scheduledTime": s.get("target_time", s.get("scheduled_time", s.get("time", ""))),
                "status":        "Waiting" if status in ("Pending", "PENDING") else "Overdue",
                "priority":      priority,
            })
    return _sanitize(result)


@app.put("/verifications/{schedule_id}")
def update_verification(schedule_id: str, body: Dict[str, Any] = Body(...)):
    """Update a verification queue item status."""
    repo = _schedules()
    new_status = body.get("status", "Pending")
    _safe_db_call(lambda: repo.collection.update_one({"schedule_id": schedule_id}, {"$set": {"status": new_status}}))
    return {"message": "Verification updated"}



# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
