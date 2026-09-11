import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.connection import get_db

db = get_db()
res1 = db["daily_schedule"].update_many(
    {"patient_id": "PAT-TEST-E2E"},
    {"$set": {"target_time": "22:17", "status": "PENDING"}}
)
rx = db["prescriptions"].find_one({"patient_id": "PAT-TEST-E2E"}, {"_id": 0})
sched = db["daily_schedule"].find_one({"patient_id": "PAT-TEST-E2E"}, {"_id": 0})

print("=" * 55)
print("  PATIENT SCHEDULE UPDATED IN MONGODB")
print("=" * 55)
print(f"Patient ID        : PAT-TEST-E2E (Arjun Verma)")
print(f"Prescribed Drug   : {rx.get('medicine_name')} {rx.get('strength')}")
print(f"Scheduled Dose Time: {sched.get('target_time')} IST (10:17 PM)")
print(f"Schedule Status   : {sched.get('status')}")
print("=" * 55)
