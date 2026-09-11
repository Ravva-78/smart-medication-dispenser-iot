"""
Developer App 06: End-to-End System Validation Tool.

Purpose:
    Demonstrates the entire production pipeline flow from Camera/Test Image
    through all 5 bounded context subsystems, displaying each contract as it
    is produced. Every subsystem consumes the REAL output of the previous one.

Data Flow:
    Camera / Test Image
        │
        ▼
    Vision (Pipeline) → InspectionResult
        │
        ▼
    Inventory (InventoryManager) → InventoryEvent
        │
        ▼
    OCR (OCREntityParser) → MedicineIdentity
        │
        ▼
    Clinical (ClinicalDecisionManager) → ComplianceDecision
        │
        ▼
    Alert (AlertManager) → AlertMessage[]
"""

import sys
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta
import cv2
import numpy as np
import streamlit as st

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.pipeline import Pipeline
from inventory.manager import InventoryManager
from ocr.parser import OCREntityParser
from clinical.manager import ClinicalDecisionManager
from clinical.models import Prescription, DoseSchedule
from alerting.manager import AlertManager
from alerting.dispatchers import MockAlertDispatcher

st.set_page_config(page_title="06 - E2E System Validation", page_icon="🏭", layout="wide")
st.title("🏭 06. End-to-End System Validation")
st.caption("Full production pipeline: Image → Vision → Inventory → OCR → Clinical → Alert")

# ─── Sidebar Configuration ──────────────────────────────────────────────────────
st.sidebar.header("📸 Image Input")

# Collect available dataset images
dataset_dir = ROOT / "dataset" / "images" / "train"
available_images = sorted([f for f in dataset_dir.glob("*.png")])
image_names = [f.name for f in available_images]

input_mode = st.sidebar.radio("Input Mode", ["Dataset Image", "Upload Image"])

img_bgr = None
img_source_name = "Unknown"

if input_mode == "Dataset Image" and image_names:
    selected_name = st.sidebar.selectbox("Select Image", image_names)
    img_path = dataset_dir / selected_name
    img_bgr = cv2.imread(str(img_path))
    img_source_name = selected_name
elif input_mode == "Upload Image":
    uploaded = st.sidebar.file_uploader("Upload Blister Strip Image", type=["png", "jpg", "jpeg"])
    if uploaded is not None:
        file_bytes = np.frombuffer(uploaded.read(), dtype=np.uint8)
        img_bgr = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        img_source_name = uploaded.name

st.sidebar.markdown("---")
st.sidebar.header("📋 Prescription Context")
patient_id = st.sidebar.text_input("Patient ID", value="patient_e2e_001")
prescribed_med = st.sidebar.text_input("Prescribed Medicine", value="Paracetamol")
prescribed_strength = st.sidebar.text_input("Prescribed Strength", value="500mg")

st.sidebar.markdown("---")
st.sidebar.header("🔍 OCR Input")
st.sidebar.caption("In production this comes from camera OCR. For validation, provide simulated text.")
ocr_raw_text = st.sidebar.text_area("Simulated OCR Text", value="PARACETAMOL 500mg BATCH-2026-09 EXP 12/2028")

st.sidebar.markdown("---")
st.sidebar.header("⏰ Schedule Context")
sched_offset = st.sidebar.slider("Schedule Offset (minutes from now)", -180, 180, 0, step=15)

# ─── Pipeline Flow ───────────────────────────────────────────────────────────────
if img_bgr is None:
    st.info("👈 Select or upload a blister strip image to begin the end-to-end validation.")
    st.stop()

# Show input image
st.subheader("📸 Stage 0 — Input Image")
_, img_col, _ = st.columns([1, 2, 1])
with img_col:
    st.image(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB), caption=f"Input: {img_source_name}", width=400)

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════════
# STAGE 1: VISION
# ═══════════════════════════════════════════════════════════════════════════════════
st.subheader("🔬 Stage 1 — Vision Pipeline → InspectionResult")
with st.spinner("Running Vision Pipeline (Model A → Perspective → Model B → Extractor → Model C)..."):
    t0 = time.time()
    pipe = Pipeline.from_defaults()
    inspection_result = pipe.run(img_bgr)
    vision_time = time.time() - t0

# Vision metrics
v1, v2, v3, v4 = st.columns(4)
v1.metric("Total Pockets", inspection_result.total)
v2.metric("Present", inspection_result.present)
v3.metric("Missing", inspection_result.missing)
v4.metric("Vision Time", f"{vision_time:.2f}s")

# Execution report
with st.expander("📋 Pipeline Execution Report", expanded=False):
    for line in inspection_result.execution_report:
        st.text(line)

# Visual result
if inspection_result.stages and inspection_result.stages.rectified is not None:
    vis = inspection_result.stages.rectified.copy()
    for p in inspection_result.pockets:
        x1, y1, x2, y2 = p.bbox
        color = (0, 255, 0) if p.class_name == "present" else (0, 0, 255)
        cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
        label = f"P{p.index}: {p.class_name} ({p.confidence:.0%})"
        cv2.putText(vis, label, (x1, max(15, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1)
    _, vis_col, _ = st.columns([1, 2, 1])
    with vis_col:
        st.image(cv2.cvtColor(vis, cv2.COLOR_BGR2RGB), caption="Vision Output: Pockets Detected & Classified", width=500)

# InspectionResult contract
with st.expander("📦 InspectionResult Contract (JSON)", expanded=False):
    st.json(inspection_result.to_dict())

st.success(f"✅ **Vision** → InspectionResult: {inspection_result.total} pockets | {inspection_result.present} present | {inspection_result.missing} missing")

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════════
# STAGE 2: INVENTORY
# ═══════════════════════════════════════════════════════════════════════════════════
st.subheader("📦 Stage 2 — Inventory Manager → InventoryEvent")

now_utc = datetime.now(timezone.utc)
inv_mgr = InventoryManager()

# Create baseline (full strip) then current inspection
from pipeline.inspection_result import PocketResult as PR, InspectionResult as IR
baseline_pockets = [PR(index=i, class_name="present", confidence=0.99, bbox=(0,0,10,10))
                    for i in range(1, inspection_result.total + 1)]
baseline_insp = IR(total=inspection_result.total, present=inspection_result.total, missing=0,
                   avg_confidence=0.99, pockets=baseline_pockets)

state_base, evt_base = inv_mgr.from_inspection(
    baseline_insp, strip_id="strip_e2e_001", inspection_time=now_utc - timedelta(minutes=10)
)

# Now apply real inspection result
state_curr, inventory_event = inv_mgr.from_inspection(
    inspection_result, strip_id="strip_e2e_001", inspection_time=now_utc
)

i1, i2, i3, i4 = st.columns(4)
i1.metric("Event Type", inventory_event.event_type.value)
i2.metric("Removed Slots", str(inventory_event.removed_slots))
i3.metric("Delta Missing", str(inventory_event.delta_missing))
i4.metric("Is Material", "YES" if inventory_event.is_material_change else "NO")

with st.expander("📦 InventoryEvent Contract (JSON)", expanded=False):
    st.json(inventory_event.to_dict())

if inventory_event.is_material_change:
    st.success(f"✅ **Inventory** → InventoryEvent: `{inventory_event.event_type.value}` | Removed slots: {inventory_event.removed_slots}")
else:
    st.info(f"ℹ️ **Inventory** → InventoryEvent: `{inventory_event.event_type.value}` | No material change")

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════════
# STAGE 3: OCR
# ═══════════════════════════════════════════════════════════════════════════════════
st.subheader("🔍 Stage 3 — OCR Parser → MedicineIdentity")

medicine_identity = OCREntityParser.parse(ocr_raw_text)

o1, o2, o3, o4 = st.columns(4)
o1.metric("Medicine", medicine_identity.medicine_name)
o2.metric("Strength", medicine_identity.strength)
o3.metric("Batch", medicine_identity.batch_number or "N/A")
o4.metric("Expiry", medicine_identity.expiry_date or "N/A")

with st.expander("📦 MedicineIdentity Contract (JSON)", expanded=False):
    st.json(medicine_identity.to_dict())

st.success(f"✅ **OCR** → MedicineIdentity: {medicine_identity.medicine_name} {medicine_identity.strength}")

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════════
# STAGE 4: CLINICAL
# ═══════════════════════════════════════════════════════════════════════════════════
st.subheader("⚖️ Stage 4 — Clinical Decision Engine → ComplianceDecision")

rx = Prescription(
    prescription_id="rx_e2e_001",
    patient_id=patient_id,
    medicine_name=prescribed_med,
    strength=prescribed_strength,
)
sched = DoseSchedule(
    schedule_id="sched_e2e_001",
    prescription_id="rx_e2e_001",
    scheduled_time=now_utc + timedelta(minutes=sched_offset),
    grace_period_minutes=30,
)

clinical_mgr = ClinicalDecisionManager()
compliance_decision = clinical_mgr.evaluate_event(
    event=inventory_event,
    prescription=rx,
    identity=medicine_identity,
    schedule=sched,
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Outcome", compliance_decision.outcome.value)
c2.metric("Actionable", "YES" if compliance_decision.actionable else "NO")
c3.metric("Patient ID", compliance_decision.patient_id)
c4.metric("Decision ID", compliance_decision.decision_id)

# Color-coded outcome
outcome_v = compliance_decision.outcome.value
if outcome_v == "CORRECT_DOSE":
    st.success(f"🟢 **PASS**: {compliance_decision.reason}")
elif outcome_v in ("WRONG_MEDICINE", "EXPIRED_MEDICINE"):
    st.error(f"🚨 **CRITICAL**: {compliance_decision.reason}")
elif outcome_v in ("DOSE_MISSED", "EXTRA_DOSE"):
    st.warning(f"⚠️ **WARNING**: {compliance_decision.reason}")
else:
    st.info(f"ℹ️ **{outcome_v}**: {compliance_decision.reason}")

with st.expander("📦 ComplianceDecision Contract (JSON)", expanded=False):
    st.json(compliance_decision.to_dict())

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════════
# STAGE 5: ALERT
# ═══════════════════════════════════════════════════════════════════════════════════
st.subheader("🔔 Stage 5 — Alert Engine → AlertMessage[]")

mock_dispatcher = MockAlertDispatcher()
alert_mgr = AlertManager(dispatchers=[mock_dispatcher])
alert_messages = alert_mgr.process_decision(compliance_decision)

a1, a2 = st.columns(2)
a1.metric("Alerts Dispatched", len(alert_messages))
a2.metric("Dispatcher", "MockAlertDispatcher")

if alert_messages:
    for idx, msg in enumerate(alert_messages):
        sev = msg.severity.value
        ch = msg.channel.value
        # Audit trail
        with st.expander(f"🔔 Alert #{idx+1} — `{msg.alert_id}`", expanded=True):
            trail_cols = st.columns(6)
            trail_cols[0].markdown("**⏱️ Time**")
            trail_cols[0].code(msg.timestamp.strftime("%H:%M:%S") if hasattr(msg.timestamp, 'strftime') else str(msg.timestamp))
            trail_cols[1].markdown("**📥 Input**")
            trail_cols[1].code(f"Decision\n{compliance_decision.decision_id}")
            trail_cols[2].markdown("**🎯 Outcome**")
            trail_cols[2].code(compliance_decision.outcome.value)
            trail_cols[3].markdown("**⚡ Severity**")
            sev_icon = "🔴" if sev == "CRITICAL" else "🟡" if sev == "WARNING" else "🟢"
            trail_cols[3].code(f"{sev_icon} {sev}")
            trail_cols[4].markdown("**📡 Channel**")
            trail_cols[4].code(ch)
            trail_cols[5].markdown("**✅ Status**")
            trail_cols[5].code("DELIVERED")

            st.markdown(
                f"```\n"
                f"ComplianceDecision ({compliance_decision.decision_id})\n"
                f"         │\n"
                f"         ▼\n"
                f"  Outcome: {compliance_decision.outcome.value}\n"
                f"         │\n"
                f"         ▼\n"
                f"  Mapped → Severity: {sev}\n"
                f"         │\n"
                f"         ▼\n"
                f"  Routed → Channel: {ch}\n"
                f"         │\n"
                f"         ▼\n"
                f"  Dispatched → {msg.title}\n"
                f"         │\n"
                f"         ▼\n"
                f"  ✅ DELIVERED (Alert ID: {msg.alert_id})\n"
                f"```"
            )
else:
    st.info("No alerts dispatched for this decision outcome.")

with st.expander("📦 AlertMessage[] Contracts (JSON)", expanded=False):
    st.json([m.to_dict() for m in alert_messages])

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════════
# END-TO-END SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════════
st.subheader("📊 End-to-End Pipeline Summary")

st.markdown(
    f"```\n"
    f"{'='*60}\n"
    f"  END-TO-END PIPELINE EXECUTION REPORT\n"
    f"{'='*60}\n"
    f"\n"
    f"  📸 Input Image\n"
    f"  ✓ Loaded: {img_source_name}\n"
    f"\n"
    f"  🔬 Stage 1 — Vision Pipeline\n"
    f"  ✓ InspectionResult: {inspection_result.total} pockets\n"
    f"    Present: {inspection_result.present} | Missing: {inspection_result.missing}\n"
    f"    Time: {vision_time:.2f}s\n"
    f"\n"
    f"  📦 Stage 2 — Inventory Manager\n"
    f"  ✓ InventoryEvent: {inventory_event.event_type.value}\n"
    f"    Removed Slots: {inventory_event.removed_slots}\n"
    f"    Material Change: {'YES' if inventory_event.is_material_change else 'NO'}\n"
    f"\n"
    f"  🔍 Stage 3 — OCR Parser\n"
    f"  ✓ MedicineIdentity:\n"
    f"    Medicine: {medicine_identity.medicine_name}\n"
    f"    Strength: {medicine_identity.strength}\n"
    f"    Batch: {medicine_identity.batch_number or 'N/A'}\n"
    f"    Expiry: {medicine_identity.expiry_date or 'N/A'}\n"
    f"\n"
    f"  ⚖️ Stage 4 — Clinical Decision Engine\n"
    f"  ✓ ComplianceDecision: {compliance_decision.outcome.value}\n"
    f"    Reason: {compliance_decision.reason}\n"
    f"    Actionable: {'YES' if compliance_decision.actionable else 'NO'}\n"
    f"\n"
    f"  🔔 Stage 5 — Alert Engine\n"
    f"  ✓ Alerts Dispatched: {len(alert_messages)}\n"
    + (
        "\n".join(
            f"    [{m.severity.value}] [{m.channel.value}] {m.title}"
            for m in alert_messages
        ) if alert_messages else "    (none)"
    )
    + f"\n\n"
    f"{'='*60}\n"
    f"  PIPELINE COMPLETE\n"
    f"{'='*60}\n"
    f"```"
)
