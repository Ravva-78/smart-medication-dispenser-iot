"""
Phase 2: Seed Test Patient Data into MongoDB Atlas.

Inserts:
  - Patient: PAT-TEST-E2E (Test Patient "Arjun Verma")
  - Device:  DEV-TEST-E2E (mapped to PAT-TEST-E2E)
  - Prescription: Paracetamol 500mg (3x/day)
  - Schedule: One dose at the CURRENT time (so clinical engine considers it ON_TIME)

Run:
  python -m qa_testing.phase2_seed_test_data
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.connection import verify_connection, get_db
from database.repositories import (
    PatientRepository,
    DeviceRepository,
    PrescriptionRepository,
    ScheduleRepository,
)


def seed_test_data():
    """Insert test patient data for E2E manual testing."""

    # 1. Verify DB connection first
    if not verify_connection():
        print("PHASE 2 FAILED: Cannot connect to MongoDB Atlas")
        sys.exit(1)

    db = get_db()
    pat_repo = PatientRepository(db)
    dev_repo = DeviceRepository(db)
    rx_repo = PrescriptionRepository(db)
    sched_repo = ScheduleRepository(db)

    # 2. Clean up any previous test data
    for repo in [pat_repo, dev_repo, rx_repo, sched_repo]:
        repo.collection.delete_many({"patient_id": "PAT-TEST-E2E"})
    dev_repo.collection.delete_many({"device_id": "DEV-TEST-E2E"})
    print("  [CLEANUP] Removed any previous PAT-TEST-E2E / DEV-TEST-E2E data")

    # 3. Insert Test Patient
    patient = {
        "patient_id": "PAT-TEST-E2E",
        "name": "Arjun Verma",
        "age": 45,
        "gender": "Male",
        "caregiver_phone": "+919999999999",
    }
    pat_repo.insert_one(patient)
    print(f"  [OK] Inserted patient: {patient['patient_id']} ({patient['name']})")

    # 4. Insert Test Device
    device = {
        "device_id": "DEV-TEST-E2E",
        "patient_id": "PAT-TEST-E2E",
        "camera_id": "CAM-TEST",
        "status": "ACTIVE",
        "registered_at": datetime.now(timezone.utc).isoformat(),
    }
    dev_repo.insert_one(device)
    print(f"  [OK] Inserted device: {device['device_id']} -> {device['patient_id']}")

    # 5. Insert Prescription (Paracetamol 500mg)
    prescription = {
        "prescription_id": "RX-TEST-01",
        "patient_id": "PAT-TEST-E2E",
        "medicine_id": "MED-001",
        "medicine_name": "Paracetamol",
        "strength": "500mg",
        "dosage_form": "Tablet",
        "times": ["08:00", "14:00", "21:00"],
        "active": True,
    }
    rx_repo.insert_one(prescription)
    print(f"  [OK] Inserted prescription: {prescription['prescription_id']} ({prescription['medicine_name']} {prescription['strength']})")

    # 6. Insert Schedule for NOW (so the dose window is ON_TIME)
    now_ist = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    target_time = now_ist.strftime("%H:%M")

    schedule = {
        "schedule_id": "SCHED-TEST-01",
        "patient_id": "PAT-TEST-E2E",
        "prescription_id": "RX-TEST-01",
        "medicine_name": "Paracetamol",
        "strength": "500mg",
        "target_time": target_time,
        "status": "PENDING",
    }
    sched_repo.insert_one(schedule)
    print(f"  [OK] Inserted schedule: {schedule['schedule_id']} (target_time={target_time} IST)")

    # 7. Verification - Read back from MongoDB
    print("\n--- VERIFICATION (Reading back from MongoDB) ---")

    found_patient = pat_repo.find_by_id("PAT-TEST-E2E")
    found_device = dev_repo.find_by_id("DEV-TEST-E2E")
    found_rx = rx_repo.find_by_patient_id("PAT-TEST-E2E")
    found_sched = sched_repo.find_by_patient_id("PAT-TEST-E2E")

    checks = {
        "Patient found in MongoDB": found_patient is not None,
        "Device found in MongoDB": found_device is not None,
        "Device maps to PAT-TEST-E2E": found_device and found_device.get("patient_id") == "PAT-TEST-E2E",
        "Prescription found": len(found_rx) > 0,
        "Prescription is Paracetamol 500mg": len(found_rx) > 0 and found_rx[0].get("medicine_name") == "Paracetamol",
        "Schedule found": len(found_sched) > 0,
        f"Schedule target_time = {target_time}": len(found_sched) > 0 and found_sched[0].get("target_time") == target_time,
    }

    all_passed = True
    for check_name, passed in checks.items():
        status = "PASS" if passed else "FAIL"
        icon = "[+]" if passed else "[-]"
        print(f"  {icon} {check_name}: {status}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("=" * 55)
        print("  PHASE 2: SEED TEST DATA -> ALL CHECKS PASSED")
        print("=" * 55)
    else:
        print("=" * 55)
        print("  PHASE 2: SOME CHECKS FAILED")
        print("=" * 55)
        sys.exit(1)


if __name__ == "__main__":
    print("=" * 55)
    print("  PHASE 2: SEED TEST PATIENT DATA INTO MONGODB")
    print("=" * 55)
    seed_test_data()
