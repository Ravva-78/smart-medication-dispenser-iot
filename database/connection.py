"""
MongoDB Atlas Connection Manager.

Purpose:
    Reads MONGODB_URI and DATABASE_NAME from .env file, initializes PyMongo client,
    verifies connectivity via ping, and provides database reference accessors.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
import certifi
from pymongo import MongoClient
from pymongo.database import Database
import dns.resolver

# Configure public DNS fallback to avoid broken system DNS/timeout issues
try:
    _custom_resolver = dns.resolver.Resolver()
    _custom_resolver.nameservers = ['8.8.8.8', '8.8.4.4', '1.1.1.1']
    dns.resolver.default_resolver = _custom_resolver
except Exception:
    pass

# Setup logger
logger = logging.getLogger(__name__)

# Load environment variables from .env in project root
ROOT = Path(__file__).parent.parent
load_dotenv(dotenv_path=ROOT / ".env")

MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME", "medicine_dispenser")

_client_instance: Optional[MongoClient] = None
_db_instance: Optional[Database] = None


def get_client() -> MongoClient:
    """
    Get or create PyMongo client singleton.

    Returns:
        MongoClient instance.
    """
    global _client_instance
    if _client_instance is None:
        if not MONGODB_URI:
            raise ValueError("MONGODB_URI environment variable is missing in .env file.")
        _client_instance = MongoClient(
            MONGODB_URI,
            tlsCAFile=certifi.where(),
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=5000,
        )
    return _client_instance


# ── In-Memory Fallback Database Classes ───────────────────────────────────────
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


def _create_fallback_db():
    db = _MemoryDB()
    
    # 1. Patients
    db["patients"].insert_many([
        {
            "patient_id":      "PAT-ARJUN-01",
            "name":            "Arjun Mehta",
            "age":             45,
            "gender":          "Male",
            "caregiver_phone": "+919876543210",
            "ward":            "Ward A",
            "bed":             "A-12",
        },
        {
            "patient_id":      "PAT-MEENA-01",
            "name":            "Meena Pillai",
            "age":             62,
            "gender":          "Female",
            "caregiver_phone": "+919876543211",
            "ward":            "Ward B",
            "bed":             "B-07",
        },
    ])
    
    # 2. Devices
    db["devices"].insert_many([
        {
            "device_id":     "DEV-ARJUN-01",
            "patient_id":    "PAT-ARJUN-01",
            "camera_id":     "CAM-ARJUN-01",
            "status":        "Online",
            "battery_level": 87,
            "slots_used":    0,
            "slots_total":   10,
            "ward":          "Ward A",
            "room":          "Room A-12",
        },
        {
            "device_id":     "DEV-MEENA-01",
            "patient_id":    "PAT-MEENA-01",
            "camera_id":     "CAM-MEENA-01",
            "status":        "Online",
            "battery_level": 92,
            "slots_used":    0,
            "slots_total":   10,
            "ward":          "Ward B",
            "room":          "Room B-07",
        },
    ])
    
    # 3. Medicine Catalogue
    db["medicine_catalogue"].insert_many([
        {
            "medicine_id": "MED-001",
            "brand": "Paracetamol",
            "generic": "Acetaminophen",
            "strengths": ["500mg", "650mg"],
            "dosage_form": "Tablet",
            "ocr_aliases": ["PARACETAMOL", "PCM", "CROCIN", "DOLO"],
            "current_stock": 150,
            "low_stock_threshold": 20,
            "expiry_date": "2027-12-31",
        },
        {
            "medicine_id": "MED-002",
            "brand": "Metformin",
            "generic": "Metformin Hydrochloride",
            "strengths": ["500mg", "850mg"],
            "dosage_form": "Tablet",
            "ocr_aliases": ["METFORMIN", "GLYCOMET"],
            "current_stock": 90,
            "low_stock_threshold": 15,
            "expiry_date": "2027-06-30",
        },
        {
            "medicine_id": "MED-003",
            "brand": "Amlodipine",
            "generic": "Amlodipine Besylate",
            "strengths": ["5mg", "10mg"],
            "dosage_form": "Tablet",
            "ocr_aliases": ["AMLODIPINE", "AMLONG"],
            "current_stock": 45,
            "low_stock_threshold": 10,
            "expiry_date": "2026-11-30",
        },
        {
            "medicine_id": "MED-004",
            "brand": "Atorvastatin",
            "generic": "Atorvastatin Calcium",
            "strengths": ["10mg", "20mg", "40mg"],
            "dosage_form": "Tablet",
            "ocr_aliases": ["ATORVASTATIN", "LIPITOR"],
            "current_stock": 60,
            "low_stock_threshold": 15,
            "expiry_date": "2028-01-31",
        },
        {
            "medicine_id": "MED-005",
            "brand": "Omeprazole",
            "generic": "Omeprazole",
            "strengths": ["20mg", "40mg"],
            "dosage_form": "Capsule",
            "ocr_aliases": ["OMEPRAZOLE", "OMEZ"],
            "current_stock": 80,
            "low_stock_threshold": 10,
            "expiry_date": "2027-08-31",
        },
    ])
    
    # 4. Prescriptions
    db["prescriptions"].insert_many([
        {
            "prescription_id": "RX-ARJUN-01",
            "patient_id":      "PAT-ARJUN-01",
            "medicine_id":     "MED-001",
            "medicine_name":   "Paracetamol",
            "strength":        "500mg",
            "dosage_form":     "Tablet",
            "doses_per_intake": 1,
            "times":           ["08:00", "14:00", "20:00"],
            "active":          True,
            "doctor":          "Dr. Sharma",
        },
        {
            "prescription_id": "RX-MEENA-01",
            "patient_id":      "PAT-MEENA-01",
            "medicine_id":     "MED-002",
            "medicine_name":   "Metformin",
            "strength":        "500mg",
            "dosage_form":     "Tablet",
            "doses_per_intake": 1,
            "times":           ["09:00", "21:00"],
            "active":          True,
            "doctor":          "Dr. Patel",
        },
    ])
    
    # 5. Schedules (IST relative to now)
    from datetime import datetime, timezone as dt_timezone, timedelta
    ist = dt_timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(ist)
    
    def _t(delta_hours):
        return (now_ist + timedelta(hours=delta_hours)).strftime("%H:%M")
        
    db["daily_schedule"].insert_many([
        {
            "schedule_id":     "SCHED-ARJUN-01",
            "patient_id":      "PAT-ARJUN-01",
            "prescription_id": "RX-ARJUN-01",
            "medicine_name":   "Paracetamol",
            "strength":        "500mg",
            "target_time":     _t(0),
            "status":          "PENDING",
            "device_id":       "DEV-ARJUN-01",
            "date":            now_ist.date().isoformat(),
        },
        {
            "schedule_id":     "SCHED-ARJUN-02",
            "patient_id":      "PAT-ARJUN-01",
            "prescription_id": "RX-ARJUN-01",
            "medicine_name":   "Paracetamol",
            "strength":        "500mg",
            "target_time":     _t(6),
            "status":          "PENDING",
            "device_id":       "DEV-ARJUN-01",
            "date":            now_ist.date().isoformat(),
        },
        {
            "schedule_id":     "SCHED-ARJUN-03",
            "patient_id":      "PAT-ARJUN-01",
            "prescription_id": "RX-ARJUN-01",
            "medicine_name":   "Paracetamol",
            "strength":        "500mg",
            "target_time":     _t(12),
            "status":          "PENDING",
            "device_id":       "DEV-ARJUN-01",
            "date":            now_ist.date().isoformat(),
        },
        {
            "schedule_id":     "SCHED-MEENA-01",
            "patient_id":      "PAT-MEENA-01",
            "prescription_id": "RX-MEENA-01",
            "medicine_name":   "Metformin",
            "strength":        "500mg",
            "target_time":     _t(0),
            "status":          "PENDING",
            "device_id":       "DEV-MEENA-01",
            "date":            now_ist.date().isoformat(),
        },
        {
            "schedule_id":     "SCHED-MEENA-02",
            "patient_id":      "PAT-MEENA-01",
            "prescription_id": "RX-MEENA-01",
            "medicine_name":   "Metformin",
            "strength":        "500mg",
            "target_time":     _t(12),
            "status":          "PENDING",
            "device_id":       "DEV-MEENA-01",
            "date":            now_ist.date().isoformat(),
        },
    ])
    
    return db


_fallback_db_instance = None


def get_db() -> Database:
    """
    Get PyMongo Database instance singleton. Falls back to in-memory DB if configuration is missing.

    Returns:
        Database instance.
    """
    global _db_instance, _fallback_db_instance
    if not MONGODB_URI:
        if _fallback_db_instance is None:
            _fallback_db_instance = _create_fallback_db()
        return _fallback_db_instance

    if _db_instance is None:
        try:
            client = get_client()
            # Force connection verification via ping to handle PyMongo's lazy connection behavior
            client.admin.command("ping")
            _db_instance = client[DATABASE_NAME]
        except Exception as err:
            logger.warning("[FAIL] Failed to connect to MongoDB Atlas: %s. Falling back to in-memory database.", err)
            if _fallback_db_instance is None:
                _fallback_db_instance = _create_fallback_db()
            _db_instance = _fallback_db_instance
    return _db_instance


def verify_connection() -> bool:
    """
    Ping MongoDB Atlas to verify connection health. Returns True for in-memory database mode too.

    Returns:
        True if connection verified (or in-memory fallback enabled).
    """
    if not MONGODB_URI:
        print("[INFO] MONGODB_URI missing; using fully populated in-memory fallback database.")
        return True
    try:
        client = get_client()
        client.admin.command("ping")
        print("[SUCCESS] Connected to MongoDB Atlas")
        print(f"Database: {DATABASE_NAME}")
        return True
    except Exception as err:
        print(f"[FAIL] Connection to MongoDB Atlas failed: {err}")
        print("[INFO] Falling back to in-memory database.")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    success = verify_connection()
    if not success:
        sys.exit(1)

