"""
Developer App 01: Computer Vision Subsystem Validation (Observable Pipeline).

Purpose:
    Isolates and validates the Vision Subsystem with full stage-by-stage observability:
    - Model Loading Diagnostics
    - Model A Strip Detection
    - Perspective Rectification
    - Model B Pocket Bounding Boxes
    - Pocket Crops Grid
    - Model C Tablet Presence Classifier
"""

import sys
from pathlib import Path
import cv2
import numpy as np
import streamlit as st

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import MODEL_A_PATH, MODEL_B_PATH, MODEL_C_PATH
from app.pipeline import Pipeline

st.set_page_config(page_title="01 - Vision Validation", page_icon="👁️", layout="wide")
st.title("👁️ 01. Vision Subsystem Developer Validation Tool")
st.caption("Observable Pipeline: Model A (Strip) -> Perspective Rectifier -> Model B (Pockets) -> Model C (Classifier)")

# Load Vision Pipeline
pipe = Pipeline.from_defaults()

# Sidebar Controls
st.sidebar.header("📸 Image Input Source")
input_method = st.sidebar.radio("Source", ["📂 Upload Image File", "📷 Live Camera Capture", "🖼️ Dataset Test Image"])

img_bgr = None
img_name = ""

if input_method == "📂 Upload Image File":
    uploaded = st.sidebar.file_uploader("Upload Blister Strip Image", type=["jpg", "jpeg", "png"])
    if uploaded is not None:
        bytes_data = np.frombuffer(uploaded.read(), np.uint8)
        img_bgr = cv2.imdecode(bytes_data, cv2.IMREAD_COLOR)
        img_name = uploaded.name

elif input_method == "📷 Live Camera Capture":
    cam = st.sidebar.camera_input("Take Photo")
    if cam is not None:
        bytes_data = np.frombuffer(cam.read(), np.uint8)
        img_bgr = cv2.imdecode(bytes_data, cv2.IMREAD_COLOR)
        img_name = "camera_capture.jpg"

elif input_method == "🖼️ Dataset Test Image":
    test_imgs = list((ROOT / "archived/Annotation_Packages/Person_1/images/test").glob("*.jpg")) + list((ROOT / "tests/fixtures").glob("*.jpg"))
    if test_imgs:
        sel_path = st.sidebar.selectbox("Choose Sample Image", [str(p) for p in test_imgs[:15]])
        img_bgr = cv2.imread(sel_path)
        img_name = Path(sel_path).name

# 1. Model Loading Diagnostics Section
st.subheader("1. System Model Weight Diagnostics")
c_d1, c_d2, c_d3 = st.columns(3)

with c_d1:
    exists_a = MODEL_A_PATH.exists()
    st.metric("Model A (Strip)", "FOUND" if exists_a else "MISSING")
    st.caption(f"`{MODEL_A_PATH.name}`")

with c_d2:
    exists_b = MODEL_B_PATH.exists()
    st.metric("Model B (Pocket)", "FOUND" if exists_b else "MISSING")
    st.caption(f"`{MODEL_B_PATH.name}`")

with c_d3:
    exists_c = MODEL_C_PATH.exists()
    st.metric("Model C (Classifier)", "FOUND" if exists_c else "MISSING")
    st.caption(f"`{MODEL_C_PATH.name}`")

st.markdown("---")

if img_bgr is not None:
    st.subheader(f"2. Pipeline Execution Report for `{img_name}` ({img_bgr.shape[1]}x{img_bgr.shape[0]} px)")

    # Run Vision Pipeline
    with st.spinner("Executing Model A -> Perspective -> Model B -> Model C..."):
        result = pipe.run(img_bgr, debug=True)

    # Display Execution Report Lines
    if result.execution_report:
        for line in result.execution_report:
            if line.startswith("✓"):
                st.success(line)
            elif line.startswith("✗"):
                st.error(line)
            else:
                st.info(line)

    # 3. Summary Metrics
    st.markdown("---")
    st.subheader("3. Inspection Summary Metrics")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Pockets Detected", result.total)
    m2.metric("Pills Present", result.present)
    m3.metric("Pills Missing", result.missing)
    m4.metric("Avg Confidence", f"{result.avg_confidence * 100:.1f}%")

    st.markdown("---")
    st.subheader("4. Stage 1 & 2: Model A Detection & Perspective Rectification")

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.image(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB), caption="Original Input Image", width=420)
    with col_s2:
        if result.stages and result.stages.rectified is not None:
            st.image(cv2.cvtColor(result.stages.rectified, cv2.COLOR_BGR2RGB), caption="Perspective Rectified View", width=420)
        else:
            st.info("Original image used for pocket detection.")

    st.markdown("---")
    st.subheader("5. Stage 3 & 4: Model B & C Pocket Detections & Classifications")

    annotated = result.stages.rectified.copy() if (result.stages and result.stages.rectified is not None) else img_bgr.copy()
    if result.pockets:
        for p in result.pockets:
            x1, y1, x2, y2 = p.bbox
            color = (0, 255, 0) if p.class_name == "present" else (0, 0, 255)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 3)
            label = f"P{p.index}: {p.class_name} ({p.confidence:.2f})"
            cv2.putText(annotated, label, (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    col_res1, col_res2 = st.columns([2, 1])
    with col_res1:
        st.image(cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB), caption=f"Pocket Detections ({result.total} Pockets Found)", width=480)
    with col_res2:
        st.write("### Per-Pocket Details")
        if result.pockets:
            details = [
                {
                    "Pocket #": p.index,
                    "Status": p.class_name.upper(),
                    "Confidence": f"{p.confidence * 100:.1f}%",
                    "Bounding Box": str(p.bbox),
                }
                for p in result.pockets
            ]
            st.dataframe(details)
        else:
            st.warning("No blister pockets detected on this image.")

    st.markdown("---")
    st.subheader("6. InspectionResult Data Contract JSON")
    st.json(result.to_dict())

else:
    st.info("👈 Upload an image, capture a photo, or choose a sample image from the left sidebar to run Vision Subsystem validation.")
