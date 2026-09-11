"""
Developer App 06: Full System Integration Validation Tool.

Purpose:
    Validates complete end-to-end pipeline integration across all bounded contexts
    (Vision -> Inventory -> OCR -> Clinical -> Alerting -> REST API).
"""

import sys
from pathlib import Path
import cv2
import numpy as np
import streamlit as st
from datetime import datetime, timezone

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.server import DispenserAPIService

st.set_page_config(page_title="06 - Master System Validation", page_icon="🚀", layout="wide")
st.title("🚀 06. Master System Pipeline Developer Validation Tool")
st.caption("Validates End-to-End System Pipeline Integration (Vision -> Inventory -> OCR -> Clinical -> Alerting -> REST API)")

service = DispenserAPIService()

st.sidebar.header("📋 Patient Prescription Settings")
patient_id = st.sidebar.text_input("Patient ID", value="patient_sys_demo")
med_name = st.sidebar.selectbox("Prescribed Medicine", ["Paracetamol", "Amoxicillin", "Ibuprofen", "Aspirin"])
med_strength = st.sidebar.selectbox("Prescribed Strength", ["500mg", "250mg", "400mg", "100mg"])
strip_id = st.sidebar.text_input("Strip ID", value="strip_sys_2026")

st.sidebar.markdown("---")
st.sidebar.header("📸 Image Input Source")
input_method = st.sidebar.radio("Source", ["Upload Image File", "Camera Capture", "Dataset Test Image"])

img_bgr = None
img_name = ""

if input_method == "Upload Image File":
    uploaded = st.sidebar.file_uploader("Upload Blister Strip Image", type=["jpg", "jpeg", "png"])
    if uploaded is not None:
        bytes_data = np.frombuffer(uploaded.read(), np.uint8)
        img_bgr = cv2.imdecode(bytes_data, cv2.IMREAD_COLOR)
        img_name = uploaded.name

elif input_method == "Camera Capture":
    cam = st.sidebar.camera_input("Take Photo")
    if cam is not None:
        bytes_data = np.frombuffer(cam.read(), np.uint8)
        img_bgr = cv2.imdecode(bytes_data, cv2.IMREAD_COLOR)
        img_name = "camera_capture.jpg"

elif input_method == "Dataset Test Image":
    test_imgs = list((ROOT / "archived/Annotation_Packages/Person_1/images/test").glob("*.jpg")) + list((ROOT / "tests/fixtures").glob("*.jpg"))
    if test_imgs:
        sel_path = st.sidebar.selectbox("Choose Sample Image", [str(p) for p in test_imgs[:15]])
        img_bgr = cv2.imread(sel_path)
        img_name = Path(sel_path).name

if img_bgr is not None:
    st.subheader(f"1. Input Frame: `{img_name}` ({img_bgr.shape[1]}x{img_bgr.shape[0]} px)")

    now_str = datetime.now(timezone.utc).isoformat()
    raw_inspection = {
        "inspection_id": "insp_sys_01",
        "image_name": img_name,
        "capture_time": now_str,
        "camera_id": "cam_sys_01",
        "total": 10,
        "present": 9,
        "missing": 1,
        "missing_indices": [4],
        "avg_confidence": 0.985,
    }
    prescription = {
        "prescription_id": "rx_sys_01",
        "patient_id": patient_id,
        "medicine_name": med_name,
        "strength": med_strength,
    }

    if st.button("▶️ Execute Full Pipeline Evaluation", type="primary"):
        response = service.process_inspection_and_evaluate(
            raw_inspection=raw_inspection,
            prescription=prescription,
            strip_id=strip_id,
            image_array=img_bgr,
        )

        if response.success:
            st.success("Master System Pipeline Executed Successfully!")
            st.json(response.data)

else:
    st.info("👈 Upload an image, capture a photo, or choose a sample image from the left sidebar to run system validation.")
