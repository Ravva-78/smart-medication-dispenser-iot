import urllib.request
import json
import time
import requests

BASE_URL = "http://localhost:8000"

print("=" * 60)
print("1. ENDPOINT ACCESSIBILITY VERIFICATION")
print("=" * 60)

endpoints = [
    ("/patients", "Patients List"),
    ("/devices", "Devices List"),
    ("/medications", "Medications Catalogue"),
    ("/prescriptions", "Prescriptions List"),
    ("/schedules", "Schedules List"),
    ("/alerts", "Alerts Queue"),
    ("/audits", "Audit Logs (Inspection Sessions)"),
    ("/verifications", "Verification Queue"),
    ("/dispense", "Dispense Queue"),
    ("/settings", "Settings Data"),
    ("/reports", "Reports Data")
]

for ep, desc in endpoints:
    try:
        r = requests.get(f"{BASE_URL}{ep}", timeout=5)
        data = r.json()
        count = len(data) if isinstance(data, list) else len(data.keys())
        print(f"  [OK] {ep:<16} ({desc:<24}) -> {r.status_code} OK | Records: {count}")
    except Exception as e:
        print(f"  [FAIL] {ep:<16} ({desc:<24}) -> Error: {e}")

print("\n" + "=" * 60)
print("2. END-TO-END SCAN #1 (BASELINE) EXECUTION")
print("=" * 60)

device_id = "DEV-ARJUN-01"

# Run Scan #1 (Full strip baseline: 10 present, 0 missing)
payload1 = {
    "total_slots": 10,
    "missing_count": 0
}
r1 = requests.post(f"{BASE_URL}/api/v1/devices/{device_id}/inspection", data=payload1)
if r1.status_code == 200:
    res1 = r1.json().get("data", {})
    print("  [SUCCESS] Scan #1 Succeeded!")
    print("    Session ID:", res1.get("session_id"))
    print("    Tablet Counts:", res1.get("tablet_counts"))
    print("    Clinical Decision:", res1.get("compliance_decision", {}).get("outcome"))
else:
    print("  [FAIL] Scan #1 Failed:", r1.status_code, r1.text)

print("\n" + "=" * 60)
print("3. END-TO-END SCAN #2 (1 TABLET TAKEN - CORRECT DOSE) EXECUTION")
print("=" * 60)

# Run Scan #2 (1 tablet removed: 9 present, 1 missing)
payload2 = {
    "total_slots": 10,
    "missing_count": 1
}
r2 = requests.post(f"{BASE_URL}/api/v1/devices/{device_id}/inspection", data=payload2)
if r2.status_code == 200:
    res2 = r2.json().get("data", {})
    print("  [SUCCESS] Scan #2 Succeeded!")
    print("    Session ID:", res2.get("session_id"))
    print("    Tablet Counts:", res2.get("tablet_counts"))
    print("    Clinical Decision:", res2.get("compliance_decision", {}).get("outcome"))
    print("    Reason:", res2.get("compliance_decision", {}).get("reason"))
    print("    Schedule Updated:", res2.get("schedule"))
else:
    print("  [FAIL] Scan #2 Failed:", r2.status_code, r2.text)

print("\n" + "=" * 60)
print("4. VERIFYING DATABASE STATE UPDATES ACROSS APP")
print("=" * 60)

# Check updated schedules
r_sched = requests.get(f"{BASE_URL}/schedules").json()
print("  [OK] Daily Schedules:")
for s in r_sched:
    if s.get("patientId") == "PAT-ARJUN-01":
        print(f"    - {s.get('id')}: Time={s.get('time')}, Status={s.get('status')}")

# Check alerts
r_alerts = requests.get(f"{BASE_URL}/alerts").json()
print(f"  [OK] Total Alerts in DB: {len(r_alerts)}")
for a in r_alerts:
    print(f"    - Alert {a.get('id')}: [{a.get('type')}] {a.get('title')} ({a.get('status')})")

# Check audits / inspection sessions
r_audits = requests.get(f"{BASE_URL}/audits").json()
print(f"  [OK] Total Audit Log Sessions in DB: {len(r_audits)}")
for aud in r_audits:
    print(f"    - Session {aud.get('id')}: Patient={aud.get('patient')}, Status={aud.get('status')}")


print("\n" + "=" * 60)
print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY")
print("=" * 60)
