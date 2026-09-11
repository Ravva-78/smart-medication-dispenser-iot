import requests
import json

BASE_URL = "http://localhost:8000"
device_id = "DEV-ARJUN-01"

print("=" * 60)
print("VERIFYING DYNAMIC TABLET COUNT WORKFLOW (e.g. Starting with 8)")
print("=" * 60)

# 1. Reset baseline by using a unique strip device session or testing starting count = 8
# Scan #1: Patient starts with 8 tablets on strip (Total 10, Missing 2 -> 8 present)
print("\n[Step 1] First Scan: Blister strip has 8 tablets remaining...")
r1 = requests.post(f"{BASE_URL}/api/v1/devices/{device_id}/inspection", data={
    "total_slots": 10,
    "missing_count": 2  # 8 present
})
res1 = r1.json().get("data", {})
print("  Scan #1 Detected Present:", res1.get("tablet_counts", {}).get("present"))
print("  Scan #1 Delta:", res1.get("tablet_counts", {}).get("delta"))
print("  Scan #1 Outcome:", res1.get("compliance_decision", {}).get("outcome"))
assert res1.get("tablet_counts", {}).get("present") == 8
assert res1.get("compliance_decision", {}).get("outcome") == "PENDING"
print("  -> First scan successfully recorded initial baseline: 8 tablets.")

# Scan #2: Patient takes 1 tablet -> 8 - 1 = 7 present (Total 10, Missing 3)
print("\n[Step 2] Second Scan: Patient took 1 dose (8 -> 7 present)...")
r2 = requests.post(f"{BASE_URL}/api/v1/devices/{device_id}/inspection", data={
    "total_slots": 10,
    "missing_count": 3  # 7 present
})
res2 = r2.json().get("data", {})
print("  Scan #2 Detected Present:", res2.get("tablet_counts", {}).get("present"))
print("  Scan #2 Delta:", res2.get("tablet_counts", {}).get("delta"))
print("  Scan #2 Outcome:", res2.get("compliance_decision", {}).get("outcome"))
print("  Scan #2 Reason:", res2.get("compliance_decision", {}).get("reason"))
assert res2.get("tablet_counts", {}).get("present") == 7
assert res2.get("tablet_counts", {}).get("delta") == -1
assert res2.get("compliance_decision", {}).get("outcome") == "CORRECT_DOSE"
print("  -> Second scan successfully verified: 8 - 1 = 7 tablets -> CORRECT_DOSE.")

print("\n" + "=" * 60)
print("DYNAMIC COUNT LOGIC VERIFIED AND VALIDATED 100%")
print("=" * 60)
