"""
Developer App 05: Alert Engine Subsystem Developer Validation Tool.

Purpose:
    Isolates and validates the Alert Engine using REAL ComplianceDecision contracts
    produced by the Clinical Decision Engine subsystem.
    Tests channel mapping, severity classification, and dispatcher execution.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
import streamlit as st

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from clinical.manager import ClinicalDecisionManager
from clinical.models import Prescription, DoseSchedule
from ocr.parser import OCREntityParser
from inventory.manager import InventoryManager
from pipeline.inspection_result import InspectionResult, PocketResult
from alerting.manager import AlertManager
from alerting.dispatchers import MockAlertDispatcher

st.set_page_config(page_title="05 - Alert Validation", page_icon="🔔", layout="wide")
st.title("🔔 05. Alert Engine Subsystem Developer Validation Tool")
st.caption("Validates Alert Channel Mapping, Severity Classification, and Dispatcher Execution using REAL ComplianceDecision contracts")

# Initialize subsystem facades
clinical_mgr = ClinicalDecisionManager()
mock_dispatcher = MockAlertDispatcher()
alert_mgr = AlertManager(dispatchers=[mock_dispatcher])

# Presets
st.sidebar.header("🧪 Alert Scenario Presets")
preset = st.sidebar.selectbox("Choose Scenario", [
    "ℹ️ Scenario 1: Correct Dose (INFO / LOG channel)",
    "🚨 Scenario 2: Wrong Medicine (CRITICAL / ALARM + CAREGIVER)",
    "⚠️ Scenario 3: Expired Medicine (CRITICAL / CAREGIVER)",
    "⚡ Scenario 4: Extra Dose / Early (WARNING / PUSH_NOTIFICATION)",
    "⏰ Scenario 5: Dose Missed (WARNING / PUSH_NOTIFICATION)",
])

p_med, p_str = "Paracetamol", "500mg"
raw_ocr = "PARACETAMOL 500mg BATCH-2026-09 EXP 12/2028"
evt_action = "REMOVE_PILL"
sched_offset_min = 0
expected_severity = "INFO"
expected_channels = ["LOG"]

if "Scenario 1" in preset:
    p_med, p_str = "Paracetamol", "500mg"
    raw_ocr = "PARACETAMOL 500mg BATCH-2026-09 EXP 12/2028"
    evt_action = "REMOVE_PILL"
    sched_offset_min = 0
    expected_severity = "INFO"
    expected_channels = ["LOG"]
elif "Scenario 2" in preset:
    p_med, p_str = "Paracetamol", "500mg"
    raw_ocr = "IBUPROFEN 400mg BATCH-IB2026 EXP 05/2027"
    evt_action = "REMOVE_PILL"
    sched_offset_min = 0
    expected_severity = "CRITICAL"
    expected_channels = ["ALARM_BUZZER", "CAREGIVER_ALERT"]
elif "Scenario 3" in preset:
    p_med, p_str = "Paracetamol", "500mg"
    raw_ocr = "PARACETAMOL 500mg BATCH-2020-01 EXP 01/2020"
    evt_action = "REMOVE_PILL"
    sched_offset_min = 0
    expected_severity = "CRITICAL"
    expected_channels = ["CAREGIVER_ALERT"]
elif "Scenario 4" in preset:
    p_med, p_str = "Paracetamol", "500mg"
    raw_ocr = "PARACETAMOL 500mg BATCH-2026-09 EXP 12/2028"
    evt_action = "REMOVE_PILL"
    sched_offset_min = 120  # Schedule 2hrs FUTURE → current time EARLY → EXTRA_DOSE
    expected_severity = "WARNING"
    expected_channels = ["PUSH_NOTIFICATION"]
elif "Scenario 5" in preset:
    p_med, p_str = "Paracetamol", "500mg"
    raw_ocr = "PARACETAMOL 500mg BATCH-2026-09 EXP 12/2028"
    evt_action = "REMOVE_PILL"
    sched_offset_min = -180  # Schedule 3hrs AGO → window MISSED → DOSE_MISSED
    expected_severity = "WARNING"
    expected_channels = ["PUSH_NOTIFICATION"]

now_utc = datetime.now(timezone.utc)
sched_time = now_utc + timedelta(minutes=sched_offset_min)

# Build real contracts through subsystem APIs
rx = Prescription(prescription_id="rx_alt_100", patient_id="patient_alt_demo",
                  medicine_name=p_med, strength=p_str)
sched = DoseSchedule(schedule_id="sched_alt_100", prescription_id="rx_alt_100",
                     scheduled_time=sched_time, grace_period_minutes=30)
identity = OCREntityParser.parse(raw_ocr)

inv_mgr = InventoryManager()
pockets_base = [PocketResult(index=i, class_name="present", confidence=0.99, bbox=(0,0,10,10)) for i in range(1, 11)]
insp_base = InspectionResult(total=10, present=10, missing=0, avg_confidence=0.99, pockets=pockets_base)
inv_mgr.from_inspection(insp_base, strip_id="strip_alt_100", inspection_time=now_utc - timedelta(minutes=5))

if evt_action == "REMOVE_PILL":
    pockets_curr = [PocketResult(index=i, class_name="missing" if i == 1 else "present", confidence=0.99, bbox=(0,0,10,10)) for i in range(1, 11)]
    insp_curr = InspectionResult(total=10, present=9, missing=1, avg_confidence=0.99, pockets=pockets_curr)
else:
    insp_curr = InspectionResult(total=10, present=10, missing=0, avg_confidence=0.99, pockets=pockets_base)

_, real_event = inv_mgr.from_inspection(insp_curr, strip_id="strip_alt_100", inspection_time=now_utc)

# Generate real ComplianceDecision
decision = clinical_mgr.evaluate_event(event=real_event, prescription=rx, identity=identity, schedule=sched)

# Dispatch through AlertManager
messages = alert_mgr.process_decision(decision)

# UI
st.subheader("1. Input ComplianceDecision (from Clinical Engine)")
m1, m2, m3 = st.columns(3)
m1.metric("Clinical Outcome", decision.outcome.value)
m2.metric("Actionable", "YES" if decision.actionable else "NO")
m3.metric("Patient ID", decision.patient_id)
st.info(f"**Reason**: {decision.reason}")

st.markdown("---")
st.subheader(f"2. Alert Dispatched Messages ({len(messages)} Notification(s))")

if messages:
    for idx, msg in enumerate(messages):
        sev = msg.severity.value
        ch = msg.channel.value
        if sev == "CRITICAL":
            st.error(f"**[{sev}] [{ch}]** {msg.title}\n\n{msg.message}")
        elif sev == "WARNING":
            st.warning(f"**[{sev}] [{ch}]** {msg.title}\n\n{msg.message}")
        else:
            st.success(f"**[{sev}] [{ch}]** {msg.title}\n\n{msg.message}")
else:
    st.info("No alert messages dispatched for this decision outcome.")

st.markdown("---")
st.subheader("3. Channel & Severity Verification")

actual_channels = [m.channel.value for m in messages]
actual_severities = [m.severity.value for m in messages]

ch_pass = set(expected_channels) == set(actual_channels)
sev_pass = all(s == expected_severity for s in actual_severities) if actual_severities else (expected_severity == "NONE")

c1, c2 = st.columns(2)
with c1:
    if ch_pass:
        st.success(f"✔ **Channel Mapping** — PASS\n\nExpected: `{expected_channels}`\n\nActual: `{actual_channels}`")
    else:
        st.error(f"✗ **Channel Mapping** — FAIL\n\nExpected: `{expected_channels}`\n\nActual: `{actual_channels}`")
with c2:
    if sev_pass:
        st.success(f"✔ **Severity Level** — PASS\n\nExpected: `{expected_severity}`\n\nActual: `{actual_severities}`")
    else:
        st.error(f"✗ **Severity Level** — FAIL\n\nExpected: `{expected_severity}`\n\nActual: `{actual_severities}`")

st.markdown("---")
st.subheader("4. Alert Audit Trail")
st.caption("Full traceability from ComplianceDecision → Severity Mapping → Channel Routing → Dispatch")

if messages:
    for idx, msg in enumerate(messages):
        with st.expander(f"🔔 Alert #{idx+1} — `{msg.alert_id}`", expanded=True):
            # Audit trail flow
            trail_cols = st.columns(6)
            trail_cols[0].markdown("**⏱️ Timestamp**")
            trail_cols[0].code(msg.timestamp.strftime("%H:%M:%S") if hasattr(msg.timestamp, 'strftime') else str(msg.timestamp))

            trail_cols[1].markdown("**📥 Input**")
            trail_cols[1].code(f"ComplianceDecision\n{decision.decision_id}")

            trail_cols[2].markdown("**🎯 Outcome**")
            trail_cols[2].code(decision.outcome.value)

            trail_cols[3].markdown("**⚡ Severity**")
            sev_color = "🔴" if msg.severity.value == "CRITICAL" else "🟡" if msg.severity.value == "WARNING" else "🟢"
            trail_cols[3].code(f"{sev_color} {msg.severity.value}")

            trail_cols[4].markdown("**📡 Channel**")
            trail_cols[4].code(msg.channel.value)

            trail_cols[5].markdown("**✅ Status**")
            trail_cols[5].code("DELIVERED")

            # Visual flow diagram
            st.markdown(
                f"```\n"
                f"ComplianceDecision ({decision.decision_id})\n"
                f"         │\n"
                f"         ▼\n"
                f"  Outcome: {decision.outcome.value}\n"
                f"         │\n"
                f"         ▼\n"
                f"  Mapped → Severity: {msg.severity.value}\n"
                f"         │\n"
                f"         ▼\n"
                f"  Routed → Channel: {msg.channel.value}\n"
                f"         │\n"
                f"         ▼\n"
                f"  Dispatched → {msg.title}\n"
                f"         │\n"
                f"         ▼\n"
                f"  ✅ DELIVERED (Alert ID: {msg.alert_id})\n"
                f"```"
            )
else:
    st.info("No alerts dispatched — no audit trail generated for this outcome.")

st.markdown("---")
st.subheader("5. Cumulative Alert History Log")
history = alert_mgr.get_alert_history()
if history:
    st.dataframe([{
        "Timestamp": h.timestamp.strftime("%H:%M:%S") if hasattr(h.timestamp, 'strftime') else str(h.timestamp),
        "Alert ID": h.alert_id,
        "Decision ID": h.decision_id,
        "Severity": h.severity.value,
        "Channel": h.channel.value,
        "Title": h.title,
        "Patient": h.patient_id,
        "Status": "✅ DELIVERED",
    } for h in history])

st.markdown("---")
st.subheader("6. AlertMessage JSON Contracts")
st.json([m.to_dict() for m in messages])

