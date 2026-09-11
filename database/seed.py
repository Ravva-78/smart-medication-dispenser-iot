"""
Database Seeder Script — Clean Slate.

Clears ALL collections and seeds fresh data:
- 2 patients: Arjun (DEV-ARJUN-01) and Meena (DEV-MEENA-01)
- Each with a prescription and dose schedule timed ~5 min from when this runs
- 5 medicines in catalogue
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.connection import verify_connection, get_db
from database.repositories import (
    MedicineCatalogueRepository,
    PatientRepository,
    DeviceRepository,
    PrescriptionRepository,
    ScheduleRepository,
    InspectionRepository,
    ComplianceRepository,
    AlertRepository,
)


def seed_database():
    """Clear all collections and seed fresh demo data."""
    print("=== Starting Clean Database Seed ===")

    db = get_db()

    # ── Repository handles ─────────────────────────────────────────────────
    med_repo  = MedicineCatalogueRepository(db)
    pat_repo  = PatientRepository(db)
    dev_repo  = DeviceRepository(db)
    rx_repo   = PrescriptionRepository(db)
    sched_repo = ScheduleRepository(db)
    insp_repo  = InspectionRepository(db)
    comp_repo  = ComplianceRepository(db)
    alert_repo = AlertRepository(db)

    # ── Clear EVERYTHING for a clean slate ────────────────────────────────
    med_repo.clear()
    pat_repo.clear()
    dev_repo.clear()
    rx_repo.clear()
    sched_repo.clear()
    insp_repo.clear()
    comp_repo.clear()
    alert_repo.clear()
    # Also clear compliance_decisions if it exists separately
    try:
        db["compliance_decisions"].delete_many({})
        db["scan_baselines"].delete_many({})
    except Exception:
        pass
    print("  [OK] Cleared all collections")

    # ── 1. Medicine Catalogue ──────────────────────────────────────────────
    medicines = [
        {
            "medicine_id": "MED-001",
            "brand": "Paracetamol",
            "generic": "Acetaminophen",
            "strengths": ["500mg", "650mg"],
            "dosage_form": "Tablet",
            "ocr_aliases": ["PARACETAMOL", "PCM", "CROCIN", "DOLO"],
        },
        {
            "medicine_id": "MED-002",
            "brand": "Metformin",
            "generic": "Metformin Hydrochloride",
            "strengths": ["500mg", "850mg"],
            "dosage_form": "Tablet",
            "ocr_aliases": ["METFORMIN", "GLYCOMET"],
        },
        {
            "medicine_id": "MED-003",
            "brand": "Amlodipine",
            "generic": "Amlodipine Besylate",
            "strengths": ["5mg", "10mg"],
            "dosage_form": "Tablet",
            "ocr_aliases": ["AMLODIPINE", "AMLONG"],
        },
        {
            "medicine_id": "MED-004",
            "brand": "Atorvastatin",
            "generic": "Atorvastatin Calcium",
            "strengths": ["10mg", "20mg", "40mg"],
            "dosage_form": "Tablet",
            "ocr_aliases": ["ATORVASTATIN", "LIPITOR"],
        },
        {
            "medicine_id": "MED-005",
            "brand": "Omeprazole",
            "generic": "Omeprazole",
            "strengths": ["20mg", "40mg"],
            "dosage_form": "Capsule",
            "ocr_aliases": ["OMEPRAZOLE", "OMEZ"],
        },
    ]
    med_repo.insert_many(medicines)
    print(f"  [OK] Inserted {len(medicines)} medicines")

    # ── 2. Patients ────────────────────────────────────────────────────────
    patients = [
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
    ]
    for p in patients:
        pat_repo.insert_one(p)
    print(f"  [OK] Inserted {len(patients)} patients")

    # ── 3. Devices ─────────────────────────────────────────────────────────
    devices = [
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
            "registered_at": datetime.now(timezone.utc).isoformat(),
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
            "registered_at": datetime.now(timezone.utc).isoformat(),
        },
    ]
    for d in devices:
        dev_repo.insert_one(d)
    print(f"  [OK] Inserted {len(devices)} devices")

    # ── 4. Prescriptions ───────────────────────────────────────────────────
    prescriptions = [
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
    ]
    for r in prescriptions:
        rx_repo.insert_one(r)
    print(f"  [OK] Inserted {len(prescriptions)} prescriptions")

    # ── 5. Daily Schedules — timed relative to now for demo ────────────────
    # Calculate IST now
    ist = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(ist)

    # Make schedule times: current time, 6h later, 12h later
    def _t(delta_hours: float) -> str:
        t = now_ist + timedelta(hours=delta_hours)
        return t.strftime("%H:%M")

    schedules = [
        {
            "schedule_id":     "SCHED-ARJUN-01",
            "patient_id":      "PAT-ARJUN-01",
            "prescription_id": "RX-ARJUN-01",
            "medicine_name":   "Paracetamol",
            "strength":        "500mg",
            "target_time":     _t(0),          # Due now — for demo scanning
            "status":          "PENDING",
            "device_id":       "DEV-ARJUN-01",
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
        },
        {
            "schedule_id":     "SCHED-MEENA-01",
            "patient_id":      "PAT-MEENA-01",
            "prescription_id": "RX-MEENA-01",
            "medicine_name":   "Metformin",
            "strength":        "500mg",
            "target_time":     _t(0),          # Due now — for demo scanning
            "status":          "PENDING",
            "device_id":       "DEV-MEENA-01",
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
        },
    ]
    sched_repo.insert_many(schedules)
    print(f"  [OK] Inserted {len(schedules)} schedule entries")
    print(f"       Arjun next dose: {schedules[0]['target_time']} IST")
    print(f"       Meena next dose: {schedules[3]['target_time']} IST")

    print("=== Database Seeding Complete ===")
    print("\nPatients:")
    print("  PAT-ARJUN-01 (Arjun Mehta) -> DEV-ARJUN-01 -> Paracetamol 500mg")
    print("  PAT-MEENA-01 (Meena Pillai) -> DEV-MEENA-01 -> Metformin 500mg")


if __name__ == "__main__":
    if verify_connection():
        seed_database()
