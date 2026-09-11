import urllib.request
import urllib.parse
import json
import os
import sys

BASE_URL = "http://localhost:8000"

print("=" * 60)
print("1. VERIFYING ALL FRONTEND REST ENDPOINTS")
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
        req = urllib.request.Request(f"{BASE_URL}{ep}")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            count = len(data) if isinstance(data, list) else len(data.keys())
            print(f"  [OK] {ep:<16} ({desc:<24}) -> 200 OK | Records: {count}")
    except Exception as e:
        print(f"  [FAIL] {ep:<16} ({desc:<24}) -> Error: {e}")

print("\n" + "=" * 60)
print("2. VERIFYING PATIENT & DEVICE MAPPING")
print("=" * 60)

with urllib.request.urlopen(f"{BASE_URL}/patients") as resp:
    patients = json.loads(resp.read().decode('utf-8'))
    for p in patients:
        print(f"  Patient: {p.get('name')} | ID: {p.get('id')} | Ward: {p.get('ward')}")

with urllib.request.urlopen(f"{BASE_URL}/devices") as resp:
    devices = json.loads(resp.read().decode('utf-8'))
    for d in devices:
        print(f"  Device: {d.get('id')} | Status: {d.get('status')} | Patient: {d.get('patientId')}")

with urllib.request.urlopen(f"{BASE_URL}/schedules") as resp:
    schedules = json.loads(resp.read().decode('utf-8'))
    for s in schedules:
        print(f"  Schedule: {s.get('id')} | Time: {s.get('time')} | Status: {s.get('status')} | Patient: {s.get('patientId')}")

print("\n" + "=" * 60)
print("3. TESTING AI INSPECTION PIPELINE WORKFLOW VIA POST")
print("=" * 60)

# Test images from user artifacts or mock test image
import cv2
import numpy as np

# Create a test synthetic image (or use existing)
test_img_path = "test_strip.jpg"
dummy_img = np.ones((300, 600, 3), dtype=np.uint8) * 200
cv2.imwrite(test_img_path, dummy_img)

import requests
device_id = "DEV-ARJUN-01"

print(f"-> Executing Scan #1 (Baseline) on {device_id}...")
with open(test_img_path, "rb") as f:
    files = {"file": ("test_strip.jpg", f, "image/jpeg")}
    r1 = requests.post(f"{BASE_URL}/api/v1/devices/{device_id}/inspection", files=files)
    if r1.status_code == 200:
        res1 = r1.json().get("data", {})
        print("  Scan #1 Success!")
        print("  Session ID:", res1.get("session_id"))
        print("  Tablet Counts:", res1.get("tablet_counts"))
        print("  Decision Outcome:", res1.get("compliance_decision", {}).get("outcome"))
    else:
        print("  Scan #1 Failed:", r1.status_code, r1.text)

print(f"\n-> Checking Schedules & Alerts after Scan #1...")
r_sched = requests.get(f"{BASE_URL}/schedules").json()
print("  Current Schedules:", [(s.get('id'), s.get('patientId'), s.get('status')) for s in r_sched])

r_alerts = requests.get(f"{BASE_URL}/alerts").json()
print("  Current Alerts in DB:", len(r_alerts))

print("\n" + "=" * 60)
print("ALL CORE VERIFICATION CHECKS COMPLETE")
print("=" * 60)
