"""
Developer App 07: Live Pill Dispenser Nurse & Caregiver Dashboard.

Purpose:
    Provides an interactive, real-time live inspection control center for nurses, caregivers,
    and system operators. Connects live laptop camera / image input directly to the FastAPI
    backend and MongoDB Atlas persistence layer.

Features:
    - Live Device & Patient Context Selector (MongoDB Atlas)
    - Live Laptop Webcam Capture & One-Click Inspection Trigger
    - Live Pipeline Execution Grid (Vision -> Inventory -> OCR -> Clinical -> Alerting)
    - Real-time Color-Coded Clinical Decision Rationale Banner
    - Dispatched Alert Badges & Audit Trail Logs
    - MongoDB Session Trace Explorer & Historical Log Inspector
"""

import sys
import time
from pathlib import Path
from datetime import datetime, timezone
import cv2
import numpy as np
import streamlit as st

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.server import DispenserAPIService
from database.connection import verify_connection, get_db
from database.repositories import (
    DeviceRepository,
    PatientRepository,
    PrescriptionRepository,
    ScheduleRepository,
    InspectionRepository,
    ComplianceRepository,
    AlertRepository,
)

st.set_page_config(page_title="PillDispenser Live Dashboard", page_icon="🏥", layout="wide")
st.title("🏥 Live Pill Dispenser Nurse & Caregiver Dashboard")
st.caption("Live Laptop Camera Inspection -> AI Pipeline -> Clinical Compliance Engine -> MongoDB Atlas Persistence")

# Initialize Backend Service & Repositories dynamically
def get_service():
    return DispenserAPIService()

service = get_service()
db = get_db()
dev_repo = DeviceRepository(db)
pat_repo = PatientRepository(db)
rx_repo = PrescriptionRepository(db)
sched_repo = ScheduleRepository(db)
insp_repo = InspectionRepository(db)
comp_repo = ComplianceRepository(db)
alert_repo = AlertRepository(db)

# ─── Sidebar Configuration ──────────────────────────────────────────────────────
st.sidebar.header("🕹️ Device & Patient Controls")

# Query registered devices from MongoDB
devices = dev_repo.list_all()
if not devices:
    st.sidebar.error("❌ No devices found in MongoDB Atlas. Run database/seed.py first!")
    st.stop()

device_map = {f"{d['device_id']} ({d.get('patient_id', 'Unassigned')})": d for d in devices}
selected_device_key = st.sidebar.selectbox("Select Active IoT Device", list(device_map.keys()))
active_device = device_map[selected_device_key]
device_id = active_device["device_id"]
patient_id = active_device["patient_id"]

# Query Patient and Prescriptions
patient = pat_repo.find_by_id(patient_id)
patient_data = patient or {}
prescriptions = rx_repo.find_by_patient_id(patient_id)
schedules = sched_repo.find_by_patient_id(patient_id)

st.sidebar.markdown("---")
st.sidebar.header("📷 Camera Input Mode")
input_mode = st.sidebar.radio("Input Source", ["📷 Live Laptop Camera", "📂 Upload Image File", "🧪 Simulation Test Case"])

st.sidebar.markdown("---")
st.sidebar.header("📡 Database Status")
db_ok = verify_connection()
if db_ok:
    st.sidebar.success("✅ **MongoDB Atlas**: Connected")
else:
    st.sidebar.warning("⚠️ **MongoDB Atlas**: Offline (Mock Fallback)")

# Session scan history array in Streamlit state
if "session_scans" not in st.session_state:
    st.session_state["session_scans"] = []

if st.sidebar.button("🗑️ Clear Local Scan Session State"):
    st.session_state["session_scans"] = []
    st.session_state.pop("last_inspection", None)
    st.rerun()

# ─── Patient Profile Header Banner ────────────────────────────────────────────────
st.subheader("👤 Active Patient & Prescription Context")
p_col1, p_col2, p_col3, p_col4 = st.columns(4)

with p_col1:
    st.markdown(f"**Patient**: {patient_data.get('name', 'Unknown')}")
    st.caption(f"ID: `{patient_id}` | Age: {patient_data.get('age', 'N/A')} ({patient_data.get('gender', 'N/A')}) | Caregiver: `{patient_data.get('caregiver_phone', 'N/A')}`")

with p_col2:
    st.markdown(f"**Device ID**: `{device_id}`")
    st.caption(f"Camera: `{active_device.get('camera_id', 'CAM-01')}` | Status: `{active_device.get('status', 'ACTIVE')}`")

with p_col3:
    rx_names = [f"• {r['medicine_name']} ({r['strength']})" for r in prescriptions] if prescriptions else ["None"]
    st.markdown("**Prescribed Medicines**:")
    for rx_line in rx_names:
        st.markdown(f"<small>{rx_line}</small>", unsafe_allow_html=True)

with p_col4:
    st.markdown("**Today's Schedule**:")
    if schedules:
        for s in schedules:
            status_icon = "🟢" if s.get("status") == "COMPLETED" else "🟡"
            st.markdown(f"<small>{status_icon} `{s.get('target_time')}` - {s.get('medicine_name')} ({s.get('status')})</small>", unsafe_allow_html=True)
    else:
        st.caption("No schedule entries for today.")

st.markdown("---")

# ─── Live Inspection Camera Section ─────────────────────────────────────────────
st.subheader(f"📸 Step 1: Capture & Inspect Blister Strip (Scan #{len(st.session_state['session_scans']) + 1})")

img_bgr = None
raw_sim = None
sim_ocr = None

if input_mode == "📷 Live Laptop Camera":
    cam_file = st.camera_input("Take Photo of Blister Strip via Laptop Webcam")
    if cam_file is not None:
        bytes_data = np.frombuffer(cam_file.read(), np.uint8)
        img_bgr = cv2.imdecode(bytes_data, cv2.IMREAD_COLOR)

elif input_mode == "📂 Upload Image File":
    uploaded = st.file_uploader("Upload Packaging or Blister Strip Photo", type=["jpg", "jpeg", "png"])
    if uploaded is not None:
        bytes_data = np.frombuffer(uploaded.read(), np.uint8)
        img_bgr = cv2.imdecode(bytes_data, cv2.IMREAD_COLOR)
        if img_bgr is not None:
            st.image(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB), caption=f"Uploaded: {uploaded.name}", width=380)
        else:
            st.error("Could not decode the uploaded image.")

elif input_mode == "🧪 Simulation Test Case":
    sim_col1, sim_col2 = st.columns(2)
    with sim_col1:
        total_p = st.number_input("Total Strip Slots", 1, 20, 10)
        missing_p = st.number_input("Missing Slots (Removed Tablets)", 0, total_p, 1)
        raw_sim = {
            "total": total_p,
            "present": total_p - missing_p,
            "missing": missing_p,
            "missing_indices": list(range(1, missing_p + 1)) if missing_p > 0 else [],
        }
    with sim_col2:
        sim_ocr = st.text_area("Simulated OCR Text", value="PARACETAMOL 500mg BATCH-2026-09 EXP 12/2028")

# Action Trigger Button
st.markdown("<br>", unsafe_allow_html=True)
run_btn = st.button("🚀 Run Live End-to-End Pipeline Inspection", type="primary", width="stretch")

if run_btn:
    if img_bgr is None and raw_sim is None:
        st.warning("⚠️ Please capture a photo via camera, upload an image, or configure a simulation test case first!")
        st.stop()

    with st.spinner("Processing live inspection across AI models & evaluating clinical compliance..."):
        fresh_service = DispenserAPIService()
        res = fresh_service.inspect_device(
            device_id=device_id,
            image_array=img_bgr,
            raw_inspection=raw_sim,
            simulated_ocr_text=sim_ocr,
        )

    if not res.success:
        st.error(f"❌ Inspection Failed: {res.error_message}")
        st.stop()

    data = res.data
    st.session_state["last_inspection"] = data
    st.session_state["session_scans"].append(data)
    st.success(f"🎉 **Inspection Session Completed**: `{data['session_id']}` (Scan #{len(st.session_state['session_scans'])})")

# ─── Live Inspection Results Display ─────────────────────────────────────────────
if "last_inspection" in st.session_state:
    data = st.session_state["last_inspection"]
    session_id = data["session_id"]
    decision = data["compliance_decision"]
    event = data["inventory_event"]
    identity = data.get("medicine_identity")
    alerts = data.get("dispatched_alerts", [])

    st.markdown("---")
    st.subheader(f"📊 Live Inspection Results — Session `{session_id}` (Scan #{len(st.session_state['session_scans'])})")

    # 1. Clinical Decision Outcome Banner
    outcome = decision["outcome"]
    reason = decision["reason"]

    if outcome == "CORRECT_DOSE":
        st.success(f"🟢 **CLINICAL OUTCOME: CORRECT DOSE VERIFIED**\n\n{reason}")
    elif outcome == "WRONG_MEDICINE":
        st.error(f"🚨 **CLINICAL OUTCOME: WRONG MEDICINE DETECTED**\n\n{reason}")
    elif outcome == "EXPIRED_MEDICINE":
        st.error(f"🚨 **CLINICAL OUTCOME: EXPIRED MEDICINE DETECTED**\n\n{reason}")
    elif outcome == "EXTRA_DOSE":
        st.error(f"⚠️ **CLINICAL OUTCOME: EXTRA DOSE / OVERDOSE DETECTED**\n\n{reason}")
    elif outcome == "DOSE_MISSED":
        st.warning(f"⚠️ **CLINICAL OUTCOME: DOSE MISSED**\n\n{reason}")
    else:
        st.info(f"ℹ️ **CLINICAL OUTCOME: {outcome}**\n\n{reason}")

    # 2. Subsystem Results Grid
    grid_c1, grid_c2, grid_c3, grid_c4 = st.columns(4)

    with grid_c1:
        st.markdown("### 🔬 Vision & Inventory")
        curr_state = event.get("current_state", {})
        st.metric("Total Slots", curr_state.get("total_slots", 10))
        st.metric("Present Tablets", curr_state.get("present_count", 10))
        st.metric("Missing Tablets", curr_state.get("missing_count", 0))
        st.caption(f"Status: **{curr_state.get('status', 'NORMAL')}**")
        st.caption(f"Event: **{event.get('event_type', 'NO_CHANGE')}**")
        st.caption(f"Delta: **{event.get('delta_present', 0):+d} Present / {event.get('delta_missing', 0):+d} Missing**")

    with grid_c2:
        st.markdown("### 🔍 OCR Extracted Identity")
        if identity:
            st.metric("Medicine Name", identity.get("medicine_name") or "Unknown")
            st.metric("Strength", identity.get("strength") or "Unknown")
            st.metric("Batch Number", identity.get("batch_number") or "N/A")
            st.caption(f"Expiry: **{identity.get('expiry_date') or 'N/A'}**")
            st.caption(f"Confidence: **{identity.get('confidence', 0):.0%}**")
        else:
            st.info("No OCR identity extracted.")

    with grid_c3:
        st.markdown("### ⚖️ Clinical Compliance")
        st.metric("Decision Outcome", decision.get("outcome"))
        st.metric("Actionable Flag", "YES" if decision.get("actionable") else "NO")
        st.caption(f"Prescription ID: `{decision.get('prescription_id')}`")
        st.caption(f"Decision ID: `{decision.get('decision_id')}`")

    with grid_c4:
        st.markdown("### 🔔 Dispatched Alerts")
        st.metric("Alerts Dispatched", len(alerts))
        if alerts:
            for a in alerts:
                sev = a.get("severity", "INFO")
                ch = a.get("channel", "LOG")
                rec = a.get("recipient", "Caregiver / System")
                st.markdown(f"**[{sev}]** `{ch}`: {a.get('title')}")
                st.caption(f"👤 Recipient: **{rec}**")
                st.caption(f"💬 Message: *{a.get('message')}*")
        else:
            st.caption("No alert notifications dispatched.")

    # 3. Dispatched Alerts Detailed Card
    if alerts:
        st.markdown("### 🚨 Dispatched Alert Notifications Details")
        for idx, a in enumerate(alerts):
            sev = a.get("severity", "INFO")
            ch = a.get("channel", "LOG")
            rec = a.get("recipient", "Caregiver")
            title = a.get("title", "")
            msg = a.get("message", "")

            if sev == "CRITICAL":
                st.error(f"🔴 **ALERT #{idx+1} [CRITICAL] — {title}**\n\n• **Channel**: `{ch}`\n• **Sent To / Target**: `{rec}`\n• **Message**: `{msg}`\n• **Timestamp**: `{a.get('timestamp')}`")
            elif sev == "WARNING":
                st.warning(f"🟡 **ALERT #{idx+1} [WARNING] — {title}**\n\n• **Channel**: `{ch}`\n• **Sent To / Target**: `{rec}`\n• **Message**: `{msg}`\n• **Timestamp**: `{a.get('timestamp')}`")
            else:
                st.info(f"🟢 **ALERT #{idx+1} [INFO] — {title}**\n\n• **Channel**: `{ch}`\n• **Sent To / Target**: `{rec}`\n• **Message**: `{msg}`\n• **Timestamp**: `{a.get('timestamp')}`")

    # 4. Session Scans Sequential Delta Timeline
    if len(st.session_state["session_scans"]) > 1:
        st.markdown("### 📈 Session Sequential Progression (Image 1 -> Image 2)")
        seq_rows = []
        for i, s in enumerate(st.session_state["session_scans"]):
            ev = s.get("inventory_event", {})
            stt = ev.get("current_state", {})
            dec = s.get("compliance_decision", {})
            seq_rows.append({
                "Scan #": f"Image #{i+1}",
                "Time": ev.get("timestamp", "")[-12:-4] if ev.get("timestamp") else "N/A",
                "Present Tablets": stt.get("present_count", "N/A"),
                "Missing Tablets": stt.get("missing_count", "N/A"),
                "Delta (Change)": f"{ev.get('delta_present', 0):+d} tablets",
                "Event Type": ev.get("event_type", "N/A"),
                "Clinical Decision": dec.get("outcome", "N/A"),
                "Action Taken": dec.get("reason", "N/A")[:50] + "...",
            })
        st.dataframe(seq_rows, width="stretch")

    # 5. Caregiver Action Summary Card
    st.markdown("### 📋 Caregiver Action Summary")
    c_card1, c_card2 = st.columns(2)
    with c_card1:
        caregiver_phone = patient_data.get("caregiver_phone", "Not configured")
        patient_name = patient_data.get("name", "Unknown")
        st.info(f"**Patient**: `{patient_name}` (ID: `{patient_id}`)\n\n**Assigned Device**: `{device_id}`\n\n**Primary Caregiver Contact**: `{caregiver_phone}`")
    with c_card2:
        st.success(f"**Scheduled Dose Time**: `{schedules[0].get('target_time') if schedules else '08:00'}`\n\n**Current Status in DB**: Saved to MongoDB Atlas `inspection_sessions`, `clinical_decisions`, `alerts`")

st.markdown("---")

# ─── MongoDB Atlas Live Session History & Audit Trail ───────────────────────────
st.subheader("📜 Step 2: MongoDB Atlas Inspection History & Session Trace")
st.caption("Live historical log query from MongoDB Atlas `inspection_sessions` & `clinical_decisions` collections")

sessions = insp_repo.list_sessions_by_patient(patient_id)

if sessions:
    history_table = []
    for sess in reversed(sessions):
        raw_ts = sess.get("timestamp", "")
        display_ts = raw_ts
        if "T" in str(raw_ts):
            try:
                dt = datetime.fromisoformat(raw_ts)
                display_ts = dt.strftime("%Y-%m-%d %I:%M:%S %p")
            except Exception:
                pass

        history_table.append({
            "Session ID": sess.get("session_id"),
            "Device ID": sess.get("device_id"),
            "Patient ID": sess.get("patient_id"),
            "Timestamp": display_ts,
            "Clinical Outcome": sess.get("status"),
            "Latency (sec)": sess.get("processing_time_sec"),
            "Database Status": "✅ PERSISTED",
        })
    st.dataframe(history_table, width="stretch")
else:
    st.info(f"No previous inspection session logs found in MongoDB Atlas for patient `{patient_id}`.")
