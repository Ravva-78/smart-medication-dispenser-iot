"""
Streamlit Real AI-Powered Computer Vision & Clinical Validation Dashboard.

Purpose:
    Provides a real-time, interactive dashboard powered by trained YOLO neural networks
    (Model A Strip Detector, Perspective Rectifier, Model B Pocket Detector, Model C Pill Present Classifier)
    and the full bounded context pipeline (Vision -> Inventory -> OCR -> Clinical -> Alerting).
"""

import sys
from pathlib import Path
import cv2
import numpy as np
import streamlit as st
from datetime import datetime, timezone

# Add repository root to python path
ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.pipeline import Pipeline
from inventory.manager import InventoryManager
from ocr.manager import OCRManager
from ocr.backends import EasyOCRBackend
from app.camera import capture_frame, CameraError
from config import ESP32_CAM_URL
from pipeline.layout import parse_layout
from clinical.manager import ClinicalDecisionManager
from clinical.models import Prescription, DoseSchedule
from alerting.manager import AlertManager
from alerting.dispatchers import MockAlertDispatcher

# Page Setup
st.set_page_config(
    page_title="Autonomous AI Medicine Dispenser Platform",
    page_icon="💊",
    layout="wide",
)

st.title("💊 Autonomous AI Medicine Dispenser Platform")
st.caption("Production AI Vision & Clinical Decision Dashboard (Real Model A / B / C Inference)")

# Initialize Pipeline & Subsystem Facades
def get_vision_pipeline(conf_a, conf_b):
    return Pipeline.from_defaults(conf_a=conf_a, conf_b=conf_b)

inv_mgr = InventoryManager()
# Real OCR only: a mock backend would report a medicine that is not on the strip.
ocr_mgr = OCRManager(backend=EasyOCRBackend())
clinical_mgr = ClinicalDecisionManager()
alert_mgr = AlertManager(dispatchers=[MockAlertDispatcher()])


# Sidebar Configuration
st.sidebar.header("📋 Patient Prescription Settings")
patient_id = st.sidebar.text_input("Patient ID", value="patient_demo_42")
med_name = st.sidebar.selectbox("Prescribed Medicine", ["Paracetamol", "Amoxicillin", "Ibuprofen", "Aspirin"])
med_strength = st.sidebar.selectbox("Prescribed Strength", ["500mg", "250mg", "400mg", "100mg"])
strip_id = st.sidebar.text_input("Strip Identifier", value="strip_demo_2026")

# Vision Sensitivity Tuning
st.sidebar.markdown("---")
st.sidebar.header("⚙️ AI Vision Sensitivity Tuning")
conf_a_val = st.sidebar.slider("Model A Strip Confidence", min_value=0.05, max_value=0.80, value=0.15, step=0.05)
conf_b_val = st.sidebar.slider("Model B Pocket Confidence", min_value=0.05, max_value=0.80, value=0.20, step=0.05)

# Optional: only compared with the detected grid when you type one (the grid itself is always detected)
expected_layout_text = st.sidebar.text_input("Expected blister layout (optional, rows x cols e.g. 5x3)", value="")
try:
    expected_layout = parse_layout(expected_layout_text)
except ValueError as err:
    expected_layout = None
    st.sidebar.error(str(err))

vision_pipeline = get_vision_pipeline(conf_a_val, conf_b_val)

# Input Source Selection
st.sidebar.markdown("---")
st.sidebar.header("📸 Image Input Source")
input_source = st.sidebar.radio("Select Source", ["📡 ESP32 Camera", "📂 Upload Image File", "📷 Live Camera Capture", "🖼️ Sample Dataset Fixture"])


def _decode(data):
    """Decode uploaded bytes; returns (image or None, error message)."""
    img = cv2.imdecode(np.asarray(bytearray(data), dtype=np.uint8), cv2.IMREAD_COLOR) if data else None
    return (img, "") if img is not None else (None, "The file is empty or is not a decodable image.")


image_bgr = None
input_error = ""
image_filename = "frame.jpg"
inv_state = None
inv_event = None
ocr_result = None
clinical_decision = None

if input_source == "📡 ESP32 Camera":
    # Capture runs only on button press and is bounded by the camera timeouts in config.py.
    cam_url = st.sidebar.text_input("ESP32 capture URL", value=ESP32_CAM_URL, placeholder="http://<esp32-ip>/capture")
    if st.sidebar.button("📸 Capture from ESP32"):
        with st.spinner("Capturing from ESP32..."):
            try:
                st.session_state["esp32_frame"] = capture_frame(cam_url)
                st.session_state["esp32_error"] = ""
                st.session_state["esp32_time"] = datetime.now().strftime("%H:%M:%S")
            except CameraError as err:
                st.session_state["esp32_frame"] = None
                st.session_state["esp32_error"] = str(err)
    image_bgr = st.session_state.get("esp32_frame")
    input_error = st.session_state.get("esp32_error", "")
    image_filename = "esp32_capture.jpg"

elif input_source == "📂 Upload Image File":
    uploaded_file = st.sidebar.file_uploader("Upload Blister Strip Photo", type=["jpg", "jpeg", "png"])
    if uploaded_file is not None:
        image_bgr, input_error = _decode(uploaded_file.read())
        image_filename = uploaded_file.name

elif input_source == "📷 Live Camera Capture":
    camera_file = st.sidebar.camera_input("Capture Photo of Blister Strip")
    if camera_file is not None:
        image_bgr, input_error = _decode(camera_file.read())
        image_filename = "camera_capture.jpg"

elif input_source == "🖼️ Sample Dataset Fixture":
    sample_images = list(Path("archived/Annotation_Packages/Person_1/images/test").glob("*.jpg")) + list(Path("tests/fixtures").glob("*.jpg"))
    if sample_images:
        selected_path = st.sidebar.selectbox("Choose Sample Image", [str(p) for p in sample_images[:10]])
        image_bgr = cv2.imread(selected_path)
        input_error = "" if image_bgr is not None else f"Could not read sample image {selected_path}."
        image_filename = Path(selected_path).name

# Main Body Tabs
tab1, tab2, tab3, tab4 = st.tabs(["🔬 AI Vision & Pipeline Execution", "📜 Subsystem Data Contracts", "📊 Patient Adherence Metrics", "🔔 Caregiver Alert History"])

with tab1:
    if input_error:
        st.error(f"🚫 **Image input failed** ({input_source}): {input_error}")
    if image_bgr is not None:
        st.subheader("1. Real-Time Vision Model Inference")
        st.caption(f"Image source: **{input_source}** | {image_bgr.shape[1]}x{image_bgr.shape[0]} px"
                   + (f" | captured {st.session_state.get('esp32_time')}" if input_source == "📡 ESP32 Camera" else ""))

        # Run AI Vision Pipeline
        with st.spinner("Running YOLO Model A (Strip), Rectifier, Model B (Pocket), Model C (Classifier)..."):
            inspection_res = vision_pipeline.run(image_bgr, conf_a=conf_a_val, conf_b=conf_b_val, debug=True,
                                                 expected_layout=expected_layout)


        # Draw Annotated Bounding Boxes
        annotated_bgr = image_bgr.copy()
        if hasattr(inspection_res, 'pockets') and len(inspection_res.pockets) > 0:
            for p in inspection_res.pockets:
                x1, y1, x2, y2 = p.bbox
                color = (0, 255, 0) if p.class_name == "present" else (0, 0, 255)
                cv2.rectangle(annotated_bgr, (x1, y1), (x2, y2), color, 3)
                cv2.putText(annotated_bgr, f"P{p.index}: {p.class_name}", (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # Display Compact Images Side-by-Side
        col_img1, col_img2 = st.columns(2)
        with col_img1:
            st.image(cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB), caption="Original Input Image", width=420)
        with col_img2:
            st.image(cv2.cvtColor(annotated_bgr, cv2.COLOR_BGR2RGB), caption=f"YOLO Pocket Detection ({inspection_res.total} Pockets Found)", width=420)

        st.markdown("---")
        st.subheader("2. End-to-End Pipeline Evaluation")

        # Raw vision outputs, kept separate from the verification verdict below.
        verification = inspection_res.verification
        v1, v2, v3, v4 = st.columns(4)
        v1.metric("Expected pockets", inspection_res.expected_total or "not set")
        v2.metric("Detected pockets", inspection_res.total)
        v3.metric("Present / Missing", f"{inspection_res.present} / {inspection_res.missing}")
        v4.metric("Lowest pocket confidence", f"{inspection_res.min_confidence:.2f}")
        grid = f"{inspection_res.layout_rows}x{inspection_res.layout_cols}"
        layout_txt = {True: "matches expected layout", False: "DOES NOT match expected layout", None: "not checked"}[inspection_res.layout_ok]
        st.caption(f"Detected grid {grid}: {layout_txt}. Verification state: **{verification}**")

        if verification == "VERIFIED" and inspection_res.missing == 0:
            st.success(f"✅ **{inspection_res.status}**")
        elif verification == "VERIFIED":
            st.warning(f"⚠️ **{inspection_res.status}** (pocket(s) {', '.join(inspection_res.missing_cells)})")
        elif verification == "NO_POCKETS":
            st.warning("⚠️ **NO BLISTER POCKETS DETECTED**: Try lowering the 'Model B Pocket Confidence' slider in the left sidebar (e.g. set to 0.15), or ensure the blister strip is clearly visible.")
        else:
            st.error(f"🚨 **{inspection_res.status}**")

        if verification != "VERIFIED":
            st.info("Inventory and clinical evaluation were not run: this inspection could not be verified. Fix the cause above and capture again.")
        else:
            now_utc = datetime.now(timezone.utc)
            prescription = Prescription(
                prescription_id="rx_demo_01",
                patient_id=patient_id,
                medicine_name=med_name,
                strength=med_strength,
            )
            schedule = DoseSchedule(
                schedule_id="sched_demo_01",
                prescription_id="rx_demo_01",
                scheduled_time=now_utc,
                grace_period_minutes=30,
            )

            # Process through Inventory Subsystem
            inv_state, inv_event = inv_mgr.from_inspection(
                result=inspection_res,
                strip_id=strip_id,
                image_name=image_filename,
                inspection_time=now_utc,
            )

            # Process through OCR Subsystem
            ocr_error = ""
            try:
                ocr_result = ocr_mgr.process_image(image_bgr, preprocess=True)
            except Exception as err:  # e.g. EasyOCR missing or model weights not downloaded
                ocr_error = str(err)

            # Process through Clinical Decision Engine, only on a verified medicine identity
            ocr_verified = ocr_result is not None and ocr_result.status.value == "VERIFIED"
            if ocr_verified:
                clinical_decision = clinical_mgr.evaluate_event(
                    event=inv_event,
                    prescription=prescription,
                    identity=ocr_result.identity,
                    schedule=schedule,
                )

            # Display Subsystem Metrics
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("Inventory Status", inv_state.status.value)
                st.metric("Tablets Present / Total", f"{inv_state.present_count} / {inv_state.total_slots}")
            with m2:
                st.metric("Inventory Event", inv_event.event_type.value)
                st.metric("Removed Slots", str(inv_event.removed_slots))
            with m3:
                if ocr_result is None:
                    st.metric("OCR", "unavailable")
                else:
                    name = ocr_result.identity.medicine_name if ocr_result.identity else "Unknown"
                    st.metric("OCR medicine" + ("" if ocr_verified else " (UNVERIFIED)"), name)
                    st.metric("OCR status", f"{ocr_result.status.value} ({ocr_result.average_confidence * 100:.0f}%)")
                st.caption(f"OCR backend: {ocr_mgr.backend.get_backend_name()}")
            with m4:
                st.metric("Clinical Decision", clinical_decision.outcome.value if clinical_decision else "not evaluated")
                st.metric("Actionable", ("YES" if clinical_decision.actionable else "NO") if clinical_decision else "-")
            st.caption("Inventory record is held in memory for this session only; nothing was written to the database.")

            # Clinical Decision Explanation Banner
            if clinical_decision is None:
                st.warning("⚠️ **Medicine identity not verified**: "
                           + (f"OCR failed ({ocr_error})." if ocr_error else "OCR could not confidently read the medicine name.")
                           + " Clinical dose evaluation was skipped; tablet counts above are unaffected.")
            elif clinical_decision.outcome.value == "CORRECT_DOSE":
                st.success(f"✅ **CLINICAL VERIFICATION PASSED**: {clinical_decision.reason}")
            elif clinical_decision.outcome.value == "WRONG_MEDICINE":
                st.error(f"🚨 **CRITICAL ALERT - WRONG MEDICINE**: {clinical_decision.reason}")
            elif clinical_decision.outcome.value == "EXPIRED_MEDICINE":
                st.error(f"⚠️ **CRITICAL ALERT - EXPIRED BATCH**: {clinical_decision.reason}")
            else:
                st.info(f"ℹ️ **CLINICAL DECISION**: {clinical_decision.reason}")

    else:
        st.info("👈 Please upload an image, capture a photo with your camera, or select a sample image from the left sidebar to run the AI Vision Pipeline!")

with tab2:
    st.subheader("Subsystem Bounded Context Payload Contracts")
    if (
        image_bgr is not None
        and inv_state is not None
        and inv_event is not None
    ):
        st.write("### 1. Inventory State Payload")
        st.json(inv_state.to_dict())

        st.write("### 2. Inventory Event Audit Record")
        st.json(inv_event.to_dict())

        st.write("### 3. OCR Result Payload")
        st.json(ocr_result.to_dict()) if ocr_result is not None else st.info("OCR did not run or failed.")

        st.write("### 4. Clinical Decision Audit Record")
        st.json(clinical_decision.to_dict()) if clinical_decision is not None else st.info("Not evaluated (medicine identity unverified).")

with tab3:
    st.subheader("Patient Adherence Statistics")
    if st.button("🔄 Refresh Adherence Stats"):
        metrics = clinical_mgr.get_patient_metrics(patient_id)
        st.json(metrics)

with tab4:
    st.subheader("Caregiver Notification Alert History")
    alerts = alert_mgr.get_alert_history(patient_id)
    if alerts:
        for a in alerts:
            st.warning(f"[{a.severity.value}] **{a.title}** ({a.timestamp.isoformat()})\n\n{a.message}")
    else:
        st.info("No caregiver alerts dispatched yet.")
