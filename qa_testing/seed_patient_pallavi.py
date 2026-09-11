import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.connection import get_db

def seed_pallavi():
    db = get_db()
    pat_repo = db["patients"]
    dev_repo = db["devices"]
    rx_repo = db["prescriptions"]
    sched_repo = db["daily_schedule"]

    patient_id = "PAT-PALLAVI-01"
    device_id = "DEV-PALLAVI-01"

    # 1. Clean up any existing records for this patient
    pat_repo.delete_many({"patient_id": patient_id})
    dev_repo.delete_many({"device_id": device_id})
    rx_repo.delete_many({"patient_id": patient_id})
    sched_repo.delete_many({"patient_id": patient_id})

    # 2. Insert Patient Demographic Record
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(ist_tz)

    patient_doc = {
        "patient_id": patient_id,
        "name": "Pallavi",
        "age": 26,
        "gender": "Female",
        "caregiver_phone": "+919876543210",
        "registered_at": now_ist.strftime("%Y-%m-%d %I:%M:%S %p IST"),
    }
    pat_repo.insert_one(patient_doc)
    print(f"  [OK] Created Patient: {patient_id} ({patient_doc['name']})")

    # 3. Insert Assigned IoT Device
    device_doc = {
        "device_id": device_id,
        "patient_id": patient_id,
        "camera_id": "CAM-PALLAVI-01",
        "status": "ACTIVE",
        "registered_at": now_ist.strftime("%Y-%m-%d %I:%M:%S %p IST"),
    }
    dev_repo.insert_one(device_doc)
    print(f"  [OK] Created Device: {device_id} -> Mapped to {patient_id}")

    # 4. Insert Prescription (3x a day: 9:00 AM, 2:00 PM, 10:55 PM)
    rx_doc = {
        "prescription_id": "RX-PALLAVI-01",
        "patient_id": patient_id,
        "medicine_id": "MED-001",
        "medicine_name": "Paracetamol",
        "strength": "500mg",
        "dosage_form": "Tablet",
        "doses_per_day": 3,
        "times": ["09:00", "14:00", "22:55"],
        "active": True,
        "instructions": "1 tablet three times daily after food",
    }
    rx_repo.insert_one(rx_doc)
    print(f"  [OK] Created Prescription: {rx_doc['prescription_id']} ({rx_doc['medicine_name']} {rx_doc['strength']})")

    # 5. Insert Daily Schedules for Today (Morning 9am, Afternoon 2pm, Night 10:55pm)
    schedules = [
        {
            "schedule_id": "SCHED-PALLAVI-01",
            "patient_id": patient_id,
            "prescription_id": "RX-PALLAVI-01",
            "medicine_name": "Paracetamol",
            "strength": "500mg",
            "target_time": "09:00",
            "status": "COMPLETED",
        },
        {
            "schedule_id": "SCHED-PALLAVI-02",
            "patient_id": patient_id,
            "prescription_id": "RX-PALLAVI-01",
            "medicine_name": "Paracetamol",
            "strength": "500mg",
            "target_time": "14:00",
            "status": "COMPLETED",
        },
        {
            "schedule_id": "SCHED-PALLAVI-03",
            "patient_id": patient_id,
            "prescription_id": "RX-PALLAVI-01",
            "medicine_name": "Paracetamol",
            "strength": "500mg",
            "target_time": "22:55",
            "status": "PENDING",
        },
    ]
    sched_repo.insert_many(schedules)
    print(f"  [OK] Created {len(schedules)} Daily Schedules (09:00, 14:00, and 22:55 IST)")

    print("\n" + "=" * 60)
    print("  PATIENT PALLAVI SETUP COMPLETED SUCCESSFULLY IN MONGODB")
    print("=" * 60)
    print(f"  Patient ID      : {patient_id} (Pallavi)")
    print(f"  IoT Device ID   : {device_id}")
    print(f"  Caregiver Phone : +919876543210")
    print(f"  Prescribed Med  : Paracetamol 500mg (3 times/day)")
    print(f"  Active Dose Time: 22:55 IST (10:55 PM Tonight)")
    print("=" * 60)

if __name__ == "__main__":
    seed_pallavi()
