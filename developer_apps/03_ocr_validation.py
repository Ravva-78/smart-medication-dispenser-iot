"""
Developer App 03: OCR Verification Subsystem Developer Validation Tool (Self-Verifying Regression Suite).

Purpose:
    Isolates and validates the OCR Verification Subsystem:
    - Image Preprocessing (Grayscale, Thresholding)
    - OCR Backend Text Extraction (Tesseract / EasyOCR / Mock)
    - OCRTextCleaner (Standardization & Regex Normalization)
    - OCREntityParser (Medicine Name, Strength, Batch #, Expiry Date)
    - 10-Case Self-Verifying Automated Regression Suite
"""

import sys
from pathlib import Path
import cv2
import numpy as np
import streamlit as st

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ocr.manager import OCRManager
from ocr.preprocessing import OCRImagePreprocessor
from ocr.cleaning import OCRTextCleaner
from ocr.parser import OCREntityParser
from ocr.backends import MockOCRBackend, EasyOCRBackend

st.set_page_config(page_title="03 - OCR Validation", page_icon="🔍", layout="wide")
st.title("🔍 03. OCR Verification Subsystem Developer Validation Tool")
st.caption("Validates Packaging Image Preprocessing -> Raw Text Extraction -> Text Cleaning -> Entity Parsing -> MedicineIdentity")

st.sidebar.header("🧪 10-Case Self-Verifying Regression Suite")

preset_cases = {
    "Manual Input": {
        "text": "",
        "exp_med": None,
        "exp_str": None,
    },
    "Case 1: Simple Medicine (PARACETAMOL 500mg)": {
        "text": "PARACETAMOL 500mg",
        "exp_med": "Paracetamol",
        "exp_str": "500mg",
    },
    "Case 2: Full Packaging (PARACETAMOL + Batch + Expiry)": {
        "text": "PARACETAMOL 500mg BATCH-2026-09 EXP 12/2028",
        "exp_med": "Paracetamol",
        "exp_str": "500mg",
        "exp_batch": "BATCH-2026-09",
    },
    "Case 3: Fields in Random Order": {
        "text": "500mg PARACETAMOL EXP:12/2028 BATCH:BATCH-2026-09",
        "exp_med": "Paracetamol",
        "exp_str": "500mg",
        "exp_batch": "BATCH-2026-09",
    },
    "Case 4: Unknown Medicine (XYZMEDICINE)": {
        "text": "XYZMEDICINE 100mg BATCH-999 EXP 01/2030",
        "exp_med": "Unknown Medicine",
        "exp_str": "100mg",
    },
    "Case 5: OCR Noise (PARACETAM0L 5OOmg)": {
        "text": "PARACETAM0L 5OOmg BATCH-2O26 EXP 12/2O28",
        "exp_med": "Paracetamol",
        "exp_str": "500mg",
    },
    "Case 6: Lowercase Input": {
        "text": "amoxicillin 250mg batch-amx901 exp 08/2029",
        "exp_med": "Amoxicillin",
        "exp_str": "250mg",
    },
    "Case 7: Mixed Case Input": {
        "text": "IbuProfen 400mG BaTch-IB2026 Exp 05/2027",
        "exp_med": "Ibuprofen",
        "exp_str": "400mg",
        "exp_batch": "BATCH-IB2026",
    },
    "Case 8: Missing Batch": {
        "text": "PANTOPRAZOLE 40mg EXP 10/2027",
        "exp_med": "Pantoprazole",
        "exp_str": "40mg",
    },
    "Case 9: Missing Expiry": {
        "text": "METFORMIN 850mg BATCH-MET850",
        "exp_med": "Metformin",
        "exp_str": "850mg",
        "exp_batch": "BATCH-MET850",
    },
}

sel_preset = st.sidebar.selectbox("Choose Preset Case", list(preset_cases.keys()))

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Input Source")
input_mode = st.sidebar.radio("Mode", ["📝 Raw Text Input (Fast Rule Test)", "📂 Upload Packaging Image", "📷 Live Camera Capture"])

raw_text_input = None
img_bgr = None

if input_mode == "📝 Raw Text Input (Fast Rule Test)":
    default_text = preset_cases[sel_preset]["text"] if sel_preset != "Manual Input" else "PARACETAM0L 5OOmg BATCH-2026-09 EXP 12/2028"
    raw_text_input = st.sidebar.text_area("Input Raw OCR Text String", value=default_text)

elif input_mode == "📂 Upload Packaging Image":
    uploaded = st.sidebar.file_uploader("Upload Packaging Photo", type=["jpg", "jpeg", "png"])
    if uploaded is not None:
        bytes_data = np.frombuffer(uploaded.read(), np.uint8)
        img_bgr = cv2.imdecode(bytes_data, cv2.IMREAD_COLOR)

elif input_mode == "📷 Live Camera Capture":
    cam = st.sidebar.camera_input("Take Photo of Medicine Box / Blister Foil")
    if cam is not None:
        bytes_data = np.frombuffer(cam.read(), np.uint8)
        img_bgr = cv2.imdecode(bytes_data, cv2.IMREAD_COLOR)

# --- Backend selection (real OCR for images) ---
st.sidebar.markdown("---")
st.sidebar.header("🤖 OCR Backend")

@st.cache_resource
def load_easyocr_backend():
    """Load EasyOCR backend once (downloads model on first run)."""
    try:
        backend = EasyOCRBackend(languages=["en"], gpu=False)
        backend._get_reader()  # Force model load
        return backend
    except Exception as e:
        return None

easyocr_backend = load_easyocr_backend()

if easyocr_backend is not None:
    ocr_backend = easyocr_backend
    st.sidebar.success(f"✅ **{ocr_backend.get_backend_name()}** — Real OCR Active")
else:
    ocr_backend = MockOCRBackend()
    st.sidebar.warning("⚠️ EasyOCR not available — using MockOCRBackend")

ocr_mgr = OCRManager(backend=ocr_backend)

if raw_text_input is not None:
    st.subheader("1. Direct Raw Text Inspection & Parsing")

    cleaned_text = OCRTextCleaner.clean(raw_text_input)
    identity = OCREntityParser.parse(cleaned_text)

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.write("### Raw OCR Input")
        st.code(raw_text_input, language="text")
    with col_t2:
        st.write("### Cleaned & Standardized Text")
        st.code(cleaned_text, language="text")

    st.markdown("---")
    st.subheader("2. Self-Verifying Regression Assertion Results")

    expected_info = preset_cases[sel_preset]
    if sel_preset != "Manual Input" and expected_info:
        exp_med = expected_info.get("exp_med")
        exp_str = expected_info.get("exp_str")
        exp_batch = expected_info.get("exp_batch")

        med_pass = (identity.medicine_name == exp_med) if exp_med else True
        str_pass = (identity.strength == exp_str) if exp_str else True
        batch_pass = (identity.batch_number == exp_batch) if exp_batch else True

        c_v1, c_v2, c_v3 = st.columns(3)
        with c_v1:
            st.metric("Medicine Name Check", identity.medicine_name, delta="PASS" if med_pass else f"FAIL (Expected {exp_med})")
        with c_v2:
            st.metric("Strength Check", identity.strength, delta="PASS" if str_pass else f"FAIL (Expected {exp_str})")
        with c_v3:
            st.metric("Batch Number Check", identity.batch_number or "N/A", delta="PASS" if batch_pass else f"FAIL (Expected {exp_batch})")

        if med_pass and str_pass and batch_pass:
            st.success(f"🎉 **TEST SUITE PASS**: All entity assertions verified for `{sel_preset}`!")
        else:
            st.error(f"❌ **TEST SUITE FAILURE**: Mismatch detected in assertions!")

    st.markdown("---")
    st.subheader("3. Parsed Medicine Identity Payload")

    expiry_str = str(identity.expiry_date) if identity.expiry_date else "N/A"

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Medicine Name", identity.medicine_name or "N/A")
    m2.metric("Strength", identity.strength or "N/A")
    m3.metric("Batch Number", identity.batch_number or "N/A")
    m4.metric("Expiry Date", expiry_str)

    st.markdown("---")
    st.subheader("4. MedicineIdentity Data Contract JSON")
    st.json(identity.to_dict())

elif img_bgr is not None:
    st.subheader(f"1. Packaging Input Image ({img_bgr.shape[1]}x{img_bgr.shape[0]} px)")

    # Stage A: Preprocessing
    preprocessed_img = OCRImagePreprocessor.preprocess(img_bgr)

    col_i1, col_i2 = st.columns(2)
    with col_i1:
        st.image(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB), caption="Original Packaging Photo", width=400)
    with col_i2:
        st.image(preprocessed_img, caption="Preprocessed Image (Grayscale + Adaptive Threshold)", width=400)

    st.markdown("---")

    # Stage B: Raw OCR Text Extraction (via REAL backend)
    st.subheader("2. OCR Pipeline Stages")
    st.caption(f"Backend: **{ocr_mgr.backend.get_backend_name()}**")

    with st.spinner(f"Running {ocr_mgr.backend.get_backend_name()} on uploaded image..."):
        raw_result = ocr_mgr.backend.extract_text(preprocessed_img)
    raw_text = raw_result.raw_text

    # Stage C: Clean the raw text
    cleaned_text = OCRTextCleaner.clean(raw_text)

    # Stage D: Parse into MedicineIdentity
    identity = OCREntityParser.parse(cleaned_text)

    # Display all 4 stages clearly
    st.markdown("#### Stage-by-Stage OCR Pipeline Flow")

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.write("### 📝 Raw OCR Text (from backend)")
        st.code(raw_text, language="text")
    with col_s2:
        st.write("### ✨ Cleaned & Standardized Text")
        st.code(cleaned_text, language="text")

    st.markdown("---")
    st.subheader("3. Parsed MedicineIdentity & Verification Verdict")

    expiry_str = str(identity.expiry_date) if identity.expiry_date else "N/A"

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Medicine Name", identity.medicine_name or "N/A")
    m2.metric("Strength", identity.strength or "N/A")
    m3.metric("Batch Number", identity.batch_number or "N/A")
    m4.metric("Expiry Date", expiry_str)

    if identity.medicine_name and identity.medicine_name != "Unknown Medicine":
        st.success(f"✅ **IDENTITY VERIFIED**: {identity.medicine_name} ({identity.strength})")
    else:
        st.warning("⚠️ Low confidence or unparseable text — medicine not identified.")

    st.markdown("---")
    st.subheader("4. MedicineIdentity Data Contract JSON")
    st.json(identity.to_dict())

    # Full pipeline flow summary
    st.markdown("---")
    st.subheader("5. OCR Pipeline Execution Summary")
    st.markdown(
        f"```\n"
        f"Image ({img_bgr.shape[1]}x{img_bgr.shape[0]} px)\n"
        f"      │\n"
        f"      ▼\n"
        f"Preprocessed (Grayscale + Threshold)\n"
        f"      │\n"
        f"      ▼\n"
        f"Raw OCR Text: \"{raw_text}\"\n"
        f"      │\n"
        f"      ▼\n"
        f"Cleaned Text: \"{cleaned_text}\"\n"
        f"      │\n"
        f"      ▼\n"
        f"MedicineIdentity:\n"
        f"  Medicine : {identity.medicine_name}\n"
        f"  Strength : {identity.strength}\n"
        f"  Batch    : {identity.batch_number or 'N/A'}\n"
        f"  Expiry   : {expiry_str}\n"
        f"```"
    )

else:
    st.info("👈 Choose a text/image input mode from the left sidebar to validate OCR text extraction and entity parsing.")
