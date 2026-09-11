"""
Developer App 04: Clinical Decision Engine Developer Validation Tool (Rule Trace).

Purpose:
    Isolates and validates the Clinical Decision Engine rules using REAL subsystem contracts.
    Shows per-rule pass/fail trace for full observability.
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
from clinical.rules import ClinicalRulesEngine
from clinical.schedule import DoseScheduler
from clinical.enums import ScheduleWindowStatus
from ocr.parser import OCREntityParser
from inventory.manager import InventoryManager
from inventory.enums import EventType
from pipeline.inspection_result import InspectionResult, PocketResult

st.set_page_config(page_title="04 - Clinical Validation", page_icon="⚖️", layout="wide")
st.title("⚖️ 04. Clinical Decision Engine Developer Validation Tool")
st.caption("Validates Clinical Compliance Rules with per-rule pass/fail trace using REAL subsystem contracts")

clinical_mgr = ClinicalDecisionManager()

# Presets
st.sidebar.header("🧪 Clinical Scenario Presets")
preset = st.sidebar.selectbox("Choose Test Scenario", [
    "✅ Scenario 1: Correct Medicine & Dose (CORRECT_DOSE)",
    "🚨 Scenario 2: Wrong Medicine Dispensed (WRONG_MEDICINE)",
    "🚨 Scenario 3: Wrong Strength Dispensed (WRONG_MEDICINE)",
    "⚠️ Scenario 4: Expired Medicine Dispensed (EXPIRED_MEDICINE)",
    "⚡ Scenario 5: Early Dose Before Window (EXTRA_DOSE)",
    "⏰ Scenario 6: Dose Window Missed (DOSE_MISSED)",
    "🔄 Scenario 7: No Change / Non-Material (PENDING)",
])

p_med, p_str = "Paracetamol", "500mg"
raw_ocr = "PARACETAMOL 500mg BATCH-2026-09 EXP 12/2028"
evt_action = "REMOVE_PILL"
sched_offset_min = 0

if "Scenario 1" in preset:
    p_med, p_str = "Paracetamol", "500mg"
    raw_ocr = "PARACETAMOL 500mg BATCH-2026-09 EXP 12/2028"
    evt_action = "REMOVE_PILL"
    sched_offset_min = 0  # ON_TIME
elif "Scenario 2" in preset:
    p_med, p_str = "Paracetamol", "500mg"
    raw_ocr = "IBUPROFEN 400mg BATCH-IB2026 EXP 05/2027"
    evt_action = "REMOVE_PILL"
    sched_offset_min = 0
elif "Scenario 3" in preset:
    p_med, p_str = "Paracetamol", "500mg"
    raw_ocr = "PARACETAMOL 250mg BATCH-2026-09 EXP 12/2028"
    evt_action = "REMOVE_PILL"
    sched_offset_min = 0
elif "Scenario 4" in preset:
    p_med, p_str = "Paracetamol", "500mg"
    raw_ocr = "PARACETAMOL 500mg BATCH-2020-01 EXP 01/2020"
    evt_action = "REMOVE_PILL"
    sched_offset_min = 0
elif "Scenario 5" in preset:
    p_med, p_str = "Paracetamol", "500mg"
    raw_ocr = "PARACETAMOL 500mg BATCH-2026-09 EXP 12/2028"
    evt_action = "REMOVE_PILL"
    sched_offset_min = 120  # Schedule is 2hrs in FUTURE → current time is EARLY → EXTRA_DOSE
elif "Scenario 6" in preset:
    p_med, p_str = "Paracetamol", "500mg"
    raw_ocr = "PARACETAMOL 500mg BATCH-2026-09 EXP 12/2028"
    evt_action = "REMOVE_PILL"
    sched_offset_min = -180  # Schedule was 3hrs AGO → window MISSED
elif "Scenario 7" in preset:
    p_med, p_str = "Paracetamol", "500mg"
    raw_ocr = "PARACETAMOL 500mg BATCH-2026-09 EXP 12/2028"
    evt_action = "NO_REMOVE"
    sched_offset_min = 0  # No pill removed → PENDING

st.sidebar.markdown("---")
st.sidebar.header("📋 Prescription Input")
patient_id = st.sidebar.text_input("Patient ID", value="patient_clin_demo")
prescribed_med = st.sidebar.text_input("Prescribed Medicine", value=p_med)
prescribed_strength = st.sidebar.text_input("Prescribed Strength", value=p_str)

st.sidebar.markdown("---")
st.sidebar.header("🔍 OCR Raw Text Input")
ocr_text_input = st.sidebar.text_area("OCR Input String", value=raw_ocr)

st.sidebar.markdown("---")
st.sidebar.header("📦 Inventory Action")
evt_choice = st.sidebar.radio("Inventory Event", ["Remove Tablet #1", "No Pill Removed"],
                              index=0 if evt_action == "REMOVE_PILL" else 1)

now_utc = datetime.now(timezone.utc)
sched_time = now_utc + timedelta(minutes=sched_offset_min)

# 1. Real Prescription & DoseSchedule
rx = Prescription(
    prescription_id="rx_clin_100",
    patient_id=patient_id,
    medicine_name=prescribed_med,
    strength=prescribed_strength,
)
sched = DoseSchedule(
    schedule_id="sched_clin_100",
    prescription_id="rx_clin_100",
    scheduled_time=sched_time,
    grace_period_minutes=30,
)

# 2. Real MedicineIdentity from OCREntityParser
identity = OCREntityParser.parse(ocr_text_input)

# 3. Real InventoryEvent from InventoryManager
inv_mgr = InventoryManager()
pockets_base = [PocketResult(index=i, class_name="present", confidence=0.99, bbox=(0,0,10,10)) for i in range(1, 11)]
insp_base = InspectionResult(total=10, present=10, missing=0, avg_confidence=0.99, pockets=pockets_base)
state_base, evt_base = inv_mgr.from_inspection(insp_base, strip_id="strip_clin_100", inspection_time=now_utc - timedelta(minutes=5))

if evt_choice == "Remove Tablet #1":
    pockets_curr = [PocketResult(index=i, class_name="missing" if i == 1 else "present", confidence=0.99, bbox=(0,0,10,10)) for i in range(1, 11)]
    insp_curr = InspectionResult(total=10, present=9, missing=1, avg_confidence=0.99, pockets=pockets_curr)
else:
    insp_curr = InspectionResult(total=10, present=10, missing=0, avg_confidence=0.99, pockets=pockets_base)

state_curr, real_event = inv_mgr.from_inspection(insp_curr, strip_id="strip_clin_100", inspection_time=now_utc)

# 4. Per-Rule Trace Evaluation
st.subheader("1. Clinical Rule Trace (Per-Rule Pass/Fail)")

# Rule 1: Medicine Match
med_ok, med_reason = ClinicalRulesEngine.evaluate_medicine_match(identity, rx)
# Rule 2: Expiry Safety
exp_ok, exp_reason = ClinicalRulesEngine.evaluate_expiry_safety(identity, now_utc)
# Rule 3: Schedule Window
window_status = DoseScheduler.evaluate_window(sched, now_utc)
sched_ok = window_status in (ScheduleWindowStatus.ON_TIME, ScheduleWindowStatus.LATE)
sched_reason = f"Window status: {window_status.value}"
# Rule 4: Inventory Change
inv_change = real_event.event_type == EventType.TABLET_REMOVED
inv_reason = f"Event type: {real_event.event_type.value}"

trace_rules = [
    ("Medicine Match", med_ok, prescribed_med, identity.medicine_name, med_reason),
    ("Strength Match", med_ok and identity.strength.lower().replace(" ","") == prescribed_strength.lower().replace(" ",""),
     prescribed_strength, identity.strength, "Strength comparison"),
    ("Expiry Safety", exp_ok, "Not Expired", str(identity.expiry_date) if identity.expiry_date else "N/A", exp_reason),
    ("Schedule Window", sched_ok, "ON_TIME or LATE", window_status.value, sched_reason),
    ("Inventory Change", inv_change, "TABLET_REMOVED", real_event.event_type.value, inv_reason),
]

all_pass = True
for rule_name, passed, expected, actual, reason in trace_rules:
    if passed:
        st.success(f"✔ **{rule_name}** — PASS | Expected: `{expected}` | Actual: `{actual}`")
    else:
        st.error(f"✗ **{rule_name}** — FAIL | Expected: `{expected}` | Actual: `{actual}` | Reason: {reason}")
        all_pass = False

st.markdown("---")

# 5. Final Decision
decision = clinical_mgr.evaluate_event(event=real_event, prescription=rx, identity=identity, schedule=sched)

st.subheader("2. Final Clinical Decision")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Outcome Verdict", decision.outcome.value)
m2.metric("Actionable?", "YES" if decision.actionable else "NO")
m3.metric("Patient ID", decision.patient_id)
m4.metric("Prescription ID", decision.prescription_id)

if decision.outcome.value == "CORRECT_DOSE":
    st.success(f"🟢 **PASS**: {decision.reason}")
elif decision.outcome.value == "WRONG_MEDICINE":
    st.error(f"🚨 **CRITICAL ALERT**: {decision.reason}")
elif decision.outcome.value == "EXPIRED_MEDICINE":
    st.warning(f"⚠️ **EXPIRED ALERT**: {decision.reason}")
elif decision.outcome.value == "DOSE_MISSED":
    st.warning(f"⏰ **MISSED**: {decision.reason}")
elif decision.outcome.value == "EXTRA_DOSE":
    st.info(f"⚡ **EXTRA DOSE**: {decision.reason}")
else:
    st.info(f"ℹ️ **{decision.outcome.value}**: {decision.reason}")

st.markdown("---")
st.subheader("3. Real Subsystem Data Contracts")

col_c1, col_c2, col_c3 = st.columns(3)
with col_c1:
    st.write("### 📋 Prescription")
    st.json(rx.to_dict())
with col_c2:
    st.write("### 🔍 Real OCR Identity")
    st.json(identity.to_dict())
with col_c3:
    st.write("### 📦 Real Inventory Event")
    st.json(real_event.to_dict())

st.markdown("---")
st.subheader("4. ComplianceDecision Payload JSON")
st.json(decision.to_dict())
