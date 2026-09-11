"""
Database Verification Test Script (Phase 5).

Purpose:
    Verifies that MongoDB Atlas collections and repositories function correctly end-to-end:
    Lookup Device -> Find Patient -> Load Prescriptions -> Lookup Medicine Master Catalogue.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.connection import verify_connection, get_db
from database.repositories import (
    DeviceRepository,
    PatientRepository,
    PrescriptionRepository,
    MedicineCatalogueRepository,
    ScheduleRepository,
)


def run_database_test():
    """Execute end-to-end repository integration test."""
    print("=== Starting Database Verification Test ===")

    db = get_db()
    dev_repo = DeviceRepository(db)
    pat_repo = PatientRepository(db)
    rx_repo = PrescriptionRepository(db)
    med_repo = MedicineCatalogueRepository(db)
    sched_repo = ScheduleRepository(db)

    # 1. Lookup Device
    device_id = "DEV-001"
    device = dev_repo.find_by_id(device_id)
    assert device is not None, f"Device {device_id} not found!"
    patient_id = device["patient_id"]
    print(f"Device Found [OK] ({device_id} -> Patient: {patient_id})")

    # 2. Lookup Patient
    patient = pat_repo.find_by_id(patient_id)
    assert patient is not None, f"Patient {patient_id} not found!"
    print(f"Patient Found [OK] ({patient['name']}, Age {patient['age']}, {patient['gender']})")

    # 3. Lookup Prescriptions
    prescriptions = rx_repo.find_by_patient_id(patient_id)
    assert len(prescriptions) > 0, f"No active prescriptions found for {patient_id}!"
    rx_summary = ", ".join([f"{r['medicine_name']} ({r['strength']})" for r in prescriptions])
    print(f"Prescription Found [OK] ({len(prescriptions)} active rx: {rx_summary})")

    # 4. Lookup Medicine Master Catalogue for prescribed drug
    rx_first = prescriptions[0]
    med_id = rx_first["medicine_id"]
    medicine = med_repo.find_by_id(med_id)
    assert medicine is not None, f"Medicine {med_id} not found in master catalogue!"
    print(f"Medicine Found [OK] ({medicine['brand']} - Generic: {medicine['generic']}, Aliases: {medicine['ocr_aliases']})")

    # 5. Lookup Daily Schedule
    schedules = sched_repo.find_by_patient_id(patient_id)
    assert len(schedules) > 0, f"No daily schedule found for {patient_id}!"
    print(f"Daily Schedule Found [OK] ({len(schedules)} entry/entries for today)")

    print("\n==========================================")
    print(" ALL DATABASE TESTS PASSED SUCCESSFULLY! ")
    print("==========================================")


if __name__ == "__main__":
    if verify_connection():
        run_database_test()
