"""
Developer App 02: Inventory Subsystem Developer Validation Tool (Stateful State Machine Inspector).

Purpose:
    Isolates and validates the stateful Inventory Subsystem:
    - InventoryState Machine Transitions
    - InventoryComparator Delta Detection
    - InventoryValidator Guarantees
    - InventoryEvent Emission & History Audit Logging
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
import streamlit as st

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.inspection_result import InspectionResult, PocketResult
from inventory.manager import InventoryManager

st.set_page_config(page_title="02 - Inventory Validation", page_icon="📦", layout="wide")
st.title("📦 02. Inventory Subsystem Stateful Validation Tool")
st.caption("Validates State Machine Transitions over time (CREATED -> TABLET_REMOVED -> NO_CHANGE) and Event History")

# Initialize Stateful InventoryManager in Streamlit Session State
if "inv_mgr" not in st.session_state:
    st.session_state.inv_mgr = InventoryManager()

if "session_events" not in st.session_state:
    st.session_state.session_events = []

inv_mgr = st.session_state.inv_mgr

# Sidebar Controls
st.sidebar.header("⚙️ Session Configuration")
strip_id = st.sidebar.text_input("Strip ID", value="strip_inv_demo_01")

if st.sidebar.button("🗑️ Reset Session & Clear History", type="secondary"):
    st.session_state.inv_mgr = InventoryManager()
    st.session_state.session_events = []
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("📥 Send Next Sequential Inspection")
total_slots = st.sidebar.slider("Total Slots", 4, 20, 10)
present_count = st.sidebar.slider("Present Tablets", 0, total_slots, 10)
missing_count = total_slots - present_count
missing_indices = st.sidebar.multiselect("Missing Pocket Indices (1-indexed)", options=list(range(1, total_slots + 1)), default=[4] if missing_count > 0 else [])

if len(missing_indices) != missing_count:
    st.sidebar.warning(f"Selected missing indices ({len(missing_indices)}) != missing count ({missing_count}).")

# Sidebar Preset Workflow Buttons
st.sidebar.markdown("---")
st.sidebar.header("🧪 Preset Test Sequences")

if st.sidebar.button("1️⃣ Step 1: Baseline 10/10 (CREATED)"):
    pockets = [PocketResult(index=i, class_name="present", confidence=0.99, bbox=(0,0,10,10)) for i in range(1, 11)]
    insp = InspectionResult(total=10, present=10, missing=0, avg_confidence=0.99, pockets=pockets)
    s, e = inv_mgr.from_inspection(insp, strip_id=strip_id, inspection_time=datetime.now(timezone.utc))
    st.session_state.session_events.append((s, e))
    st.rerun()

if st.sidebar.button("2️⃣ Step 2: Remove Pill #4 (TABLET_REMOVED)"):
    pockets = [PocketResult(index=i, class_name="missing" if i == 4 else "present", confidence=0.99, bbox=(0,0,10,10)) for i in range(1, 11)]
    insp = InspectionResult(total=10, present=9, missing=1, avg_confidence=0.99, pockets=pockets)
    s, e = inv_mgr.from_inspection(insp, strip_id=strip_id, inspection_time=datetime.now(timezone.utc))
    st.session_state.session_events.append((s, e))
    st.rerun()

if st.sidebar.button("3️⃣ Step 3: Same Frame (NO_CHANGE)"):
    pockets = [PocketResult(index=i, class_name="missing" if i == 4 else "present", confidence=0.99, bbox=(0,0,10,10)) for i in range(1, 11)]
    insp = InspectionResult(total=10, present=9, missing=1, avg_confidence=0.99, pockets=pockets)
    s, e = inv_mgr.from_inspection(insp, strip_id=strip_id, inspection_time=datetime.now(timezone.utc))
    st.session_state.session_events.append((s, e))
    st.rerun()

if st.sidebar.button("4️⃣ Step 4: Remove Pill #7 (TABLET_REMOVED)"):
    pockets = [PocketResult(index=i, class_name="missing" if i in (4, 7) else "present", confidence=0.99, bbox=(0,0,10,10)) for i in range(1, 11)]
    insp = InspectionResult(total=10, present=8, missing=2, avg_confidence=0.99, pockets=pockets)
    s, e = inv_mgr.from_inspection(insp, strip_id=strip_id, inspection_time=datetime.now(timezone.utc))
    st.session_state.session_events.append((s, e))
    st.rerun()

# Main Body
if st.button("▶️ Dispatch Manual Inspection Event", type="primary"):
    pockets = [
        PocketResult(index=i, class_name="missing" if i in missing_indices else "present", confidence=0.99, bbox=(0,0,10,10))
        for i in range(1, total_slots + 1)
    ]
    inspection = InspectionResult(
        total=total_slots,
        present=present_count,
        missing=missing_count,
        avg_confidence=0.99,
        pockets=pockets,
    )
    s, e = inv_mgr.from_inspection(inspection, strip_id=strip_id, inspection_time=datetime.now(timezone.utc))
    st.session_state.session_events.append((s, e))
    st.rerun()

# Render Session History & State Machine Timeline
st.subheader(f"📊 Active Session History for Strip: `{strip_id}` ({len(st.session_state.session_events)} Inspections Processed)")

if st.session_state.session_events:
    latest_state, latest_event = st.session_state.session_events[-1]

    # Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Current Status", latest_state.status.value)
    m2.metric("Tablets Present / Total", f"{latest_state.present_count} / {latest_state.total_slots}")
    m3.metric("Latest Event Type", latest_event.event_type.value)
    m4.metric("Newly Removed Slots", str(latest_event.removed_slots) if latest_event.removed_slots else "None")

    # Event Type Notification Banner
    if latest_event.event_type.value == "CREATED":
        st.info("🟢 **BASELINE CREATED**: Initial inventory state established.")
    elif latest_event.event_type.value == "TABLET_REMOVED":
        st.warning(f"🚨 **TABLET REMOVED**: Slot(s) {latest_event.removed_slots} newly missing!")
    elif latest_event.event_type.value == "NO_CHANGE":
        st.success("ℹ️ **NO CHANGE**: Inventory state identical to previous inspection.")

    st.markdown("---")
    st.subheader("📜 Event History Audit Sequence")

    events_table = [
        {
            "Step #": idx + 1,
            "Timestamp": e.timestamp.strftime("%H:%M:%S"),
            "Event Type": e.event_type.value,
            "Present": s.present_count,
            "Missing": s.missing_count,
            "Delta Present": e.delta_present,
            "Newly Removed Slots": str(e.removed_slots),
            "Status": s.status.value,
        }
        for idx, (s, e) in enumerate(st.session_state.session_events)
    ]
    st.dataframe(events_table)

    st.markdown("---")
    st.subheader("🔍 Latest InventoryState Payload JSON")
    st.json(latest_state.to_dict())

    st.subheader("🔍 Latest InventoryEvent Audit Payload JSON")
    st.json(latest_event.to_dict())

else:
    st.info("👈 Use the left sidebar preset buttons (Step 1 -> Step 2 -> Step 3 -> Step 4) or dispatch a manual inspection to observe state machine transitions live!")
