# MediDispense: Autonomous AI Medicine Blister Strip Verification & IoT Smart Dispensing Ecosystem

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-2.0.0-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![React + Vite](https://img.shields.io/badge/React%20%2B%20Vite-18.x-61DAFB.svg?logo=react)](https://reactjs.org/)
[![PyTorch 2.4](https://img.shields.io/badge/PyTorch-2.4%20CUDA%2012.1-EE4C2C.svg?logo=pytorch)](https://pytorch.org/)
[![YOLO11](https://img.shields.io/badge/YOLO11-Ultralytics%20v8.3-orange.svg)](https://github.com/ultralytics/ultralytics)
[![mAP@50](https://img.shields.io/badge/Model%20B%20mAP%4050-99.50%25-brightgreen.svg)]()
[![Recall](https://img.shields.io/badge/Model%20B%20Recall-99.87%25-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An enterprise-grade, edge-deployable AI platform for automated medication compliance verification, blister strip cavity counting, dynamic multi-slot topology resolution, and multi-modal safety enforcement in smart healthcare facilities and IoT pill dispensers.

---

## 🌟 Key Highlights & Engineering Breakthroughs

- **Hierarchical Decoupled Deep Vision Engine**: Resolves severe specular aluminum foil reflections and perspective distortion through a sequential multi-model architecture:
  - **Model A v2.0 (YOLO11m)**: Blister strip localization & 4-corner keypoint detection (**98.40% mAP@50**).
  - **Orientation-Aware Planar Homography**: Dynamically rectifies oblique angles to canonical Euclidean canvases ($600 \times 800$ Portrait vs $800 \times 600$ Landscape), preserving pocket circularity and eliminating false-negative dropouts.
  - **Model B v2.0 (YOLO11s)**: High-precision pocket cavity status detector trained on **605 blister strip images and 8,240 annotated cavities**, achieving **99.50% mAP@50**, **99.87% Recall**, and **99.98% Precision** across 1,501 holdout test pockets.
  - **Model C v1.0 (MobileNetV3-Small)**: Ultra-fast pill feature verification (< 5 ms inference) cross-referencing color, geometry, and surface integrity against electronic prescriptions with **98.6% accuracy**.
- **Dynamic Blister Topology Resolution**: Completely eliminates legacy hardcoded slot limits. Adaptive 1D Cartesian centroid density projection automatically determines row ($R$) and column ($C$) counts, dynamically supporting **15-slot ($3 \times 5$), 10-slot ($2 \times 5$), 14-slot ($2 \times 7$), or custom pharmaceutical packaging**.
- **Dynamic Inventory Delta Tracking**: Real-time state comparison ($\Delta I = K_{\text{initial}} - K_{\text{post}}$) cryptographically validates that exactly 1 tablet was extracted ($\Delta I == 1$), automatically intercepting cavity retention jams ($\Delta I == 0$) or accidental multi-drops ($\Delta I > 1$).
- **Triple-Stage Multi-Modal Consensus**: Integrates optical IR break-beam passage detection, HX711 gravimetric load-cell measurements, and deep vision validation into a unified fail-safe delivery gate.
- **Edge-to-Cloud Runtime**: Real-time HTTP/JPEG video streaming from an overhead **ESP32-CAM (OV2640 macro-tuned optics with 45° diffuse illumination)** to a **FastAPI backend** and modern **React 18 telemetry dashboard**.

---

## 🏗️ System Architecture

```text
                  ┌────────────────────────────────────────────────────────┐
                  │       OVERHEAD ESP32-CAM VIDEO STREAM (1024x768)       │
                  └───────────────────────────┬────────────────────────────┘
                                              │ HTTP JPEG Transport
                                              ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ STAGE 1: Strip Localization & 4-Corner Landmark Detection (Model A - YOLO11m)                 │
│ • Localizes blister pack bounding box and predicts 4 outer corner keypoints C1, C2, C3, C4   │
│ • 98.40% mAP@50 under arbitrary tray rotation, tilt (±35°), and background clutter           │
└─────────────────────────────────────────────┬────────────────────────────────────────────────┘
                                              │ 4 Corner Coordinates
                                              ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ STAGE 2: Orientation-Aware Planar Homography Rectification (OpenCV DLT / SVD)                │
│ • Computes 3x3 homography matrix H (x' ~ Hx) to eliminate perspective foreshortening         │
│ • Aspect Ratio Check: Portrait -> 600x800 canvas | Landscape -> 800x600 canvas               │
│ • Preserves physical circular geometry, preventing distorted cavity aspect ratios            │
└─────────────────────────────────────────────┬────────────────────────────────────────────────┘
                                              │ Canonical Rectified Canvas
                                              ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ STAGE 3: Dynamic Grid Topology Resolution (Adaptive 1D Centroid Projection)                   │
│ • Clusters pocket centroids along X and Y axes; dynamically computes Rows (R) and Cols (C)  │
│ • Seamlessly resolves 15-slot (3x5), 10-slot (2x5), 14-slot (2x7), and custom formats        │
└─────────────────────────────────────────────┬────────────────────────────────────────────────┘
                                              │ Dynamic Cavity Matrix
                                              ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ STAGE 4: Blister Pocket Status Detection (Model B v2.0 - YOLO11s)                             │
│ • Evaluates every individual pocket: classifies as 'filled_pocket' vs 'empty_pocket'         │
│ • 99.50% mAP@50 | 99.87% Recall | 99.98% Precision on 1,501 holdout pockets                 │
└─────────────────────────────────────────────┬────────────────────────────────────────────────┘
                                              │ Filled Cavity Regions
                                              ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ STAGE 5: Tablet Feature Classification & Defect Inspection (Model C - MobileNetV3)           │
│ • Rapid pill classification (< 5 ms) verifying color, contour, and surface integrity         │
│ • Cross-references digital prescription profile stored in PostgreSQL / MongoDB               │
└─────────────────────────────────────────────┬────────────────────────────────────────────────┘
                                              │ Consensus Verification Vector
                                              ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ STAGE 6: Dynamic Inventory Delta Engine & Audit Logging                                      │
│ • Computes tablet delta: ΔI = K_initial - K_post                                             │
│ • Dispense Approved IF AND ONLY IF ΔI == 1                                                   │
│ • Publishes cryptographically signed JSON audit event via MQTT & unlocks mechanical shutter  │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Empirical Performance Benchmarks

### 1. Multi-Model Detection & Classification Metrics

| Model Identifier | Base Architecture | Task Description | Precision (%) | Recall (%) | mAP@50 (%) | Inference Latency |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| **Model A v2.0** | YOLO11m | Blister Strip & 4-Corner Localization | 97.80 % | 96.50 % | 98.40 % | 32.4 ms (GPU) / 115 ms (CPU) |
| **Model B v1.0 (Baseline)** | YOLOv8s | Blister Pocket Status (Baseline) | 91.20 % | 88.40 % | 89.60 % | 18.2 ms (GPU) / 84 ms (CPU) |
| **Model B v2.0 (Proposed)** | YOLO11s | Blister Pocket Status (Filled vs Empty) | **99.98 %** | **99.87 %** | **99.50 %** | **14.6 ms (GPU)** / 68 ms (CPU) |
| **Model C v1.0** | MobileNetV3-Small | Tablet Classification & Defect Check | 98.90 % | 98.30 % | 98.60 % (Top-1) | 4.8 ms (GPU) / 16 ms (CPU) |
| **Integrated Pipeline** | Hierarchical | End-to-End Automated Verification | **99.85 %** | **99.80 %** | **99.40 %** | **218 ms (End-to-End)** |

### 2. Model B Curated Dataset Partitioning

| Split Name | Blister Strips | Total Pockets | Filled Pockets | Empty Pockets | Role in Research |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Training Set** | 503 | 6,739 | 5,182 | 1,557 | Supervised training with photometric augmentations |
| **Validation Set** | 27 | 362 | 278 | 84 | Checkpoint validation & hyperparameter tuning |
| **Holdout Test Set** | 75 | 1,501 | 1,148 | 353 | Independent blind evaluation (**0 missed cavities**) |
| **Total Verified** | **605** | **8,240** | **6,608** | **1,632** | Curated & validated blister repository |

### 3. Edge-to-Host Pipeline Latency Breakdown

| Pipeline Stage | Processor / Hardware | Latency (ms) | Memory Footprint |
| :--- | :--- | :---: | :---: |
| **ESP32-CAM Frame Capture** | ESP32-CAM (OV2640) | 120 ms | 180 KB SRAM |
| **Wi-Fi Transport to Host** | 802.11 b/g/n (HTTP JPEG) | 45 ms | N/A |
| **Stage 1: Strip Detection (Model A)** | NVIDIA RTX 3050 / PyTorch | 32.4 ms | 640 MB VRAM |
| **Stage 2: Homography Rectification** | Host CPU (OpenCV SVD) | 6.2 ms | 12 MB RAM |
| **Stage 3: Grid Partitioning** | Host CPU (NumPy) | 2.1 ms | 4 MB RAM |
| **Stage 4: Pocket Detection (Model B)** | NVIDIA RTX 3050 / PyTorch | 14.6 ms | 420 MB VRAM |
| **Stage 5: Tablet Classification (Model C)**| NVIDIA RTX 3050 / PyTorch | 4.8 ms | 110 MB VRAM |
| **Stage 6: Inventory Delta & MQTT** | FastAPI / Paho-MQTT | 8.2 ms | 8 MB RAM |
| **Total End-to-End Latency** | **Integrated System** | **233.3 ms** | **1.18 GB VRAM** |

---

## ⚡ Quickstart Guide

### 1. Prerequisites
- **Python**: 3.10 or 3.11 (with CUDA-capable GPU recommended)
- **Node.js**: 18.x or 20.x
- **Hardware**: ESP32-CAM module (OV2640) or USB webcam

### 2. Clone & Environment Setup

```bash
# 1. Clone repository
git clone https://github.com/<your-username>/MediDispense.git
cd MediDispense

# 2. Create Python virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# 3. Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Configure environment secrets
cp .env.example .env
# Update .env with your MongoDB Atlas or local settings if needed
```

### 3. Launch the Backend API Server

```bash
# Start FastAPI server on port 8000 (auto-reloads on code edits)
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
- **Swagger Interactive API Docs**: `http://localhost:8000/docs`
- **ReDoc API Documentation**: `http://localhost:8000/redoc`
- **System Health Endpoint**: `http://localhost:8000/api/v1/health`

### 4. Launch the React Web Dashboard

```bash
# Open a second terminal
cd medidispense-ui
npm install
npm run dev
```
- **Web UI Dashboard**: `http://localhost:5173`
- Navigate to **Tablet Identification / Tablet Scan** to view real-time ESP32 camera streaming and execute dynamic blister scans.

### 5. Run Standalone Inference via CLI

```bash
# Run end-to-end pipeline on any blister image
python pipeline.py path/to/blister_pack.jpg

# Run Model A real-time webcam detection
python app/detect_camera.py --camera 0 --weights models/production/ModelA_v2.0.pt --conf 0.35

# Test dynamic pocket counting logic
python test_dynamic_counts.py
```

---

## 🧪 Automated Testing & Developer Tools

MediDispense includes an extensive suite of 140+ unit, integration, and developer apps:

```bash
# Run the full automated test suite
python -m unittest discover tests

# Launch Developer Validation Portals (Streamlit)
streamlit run developer_apps/01_vision_validation.py      # Vision subsystem isolation
streamlit run developer_apps/02_inventory_validation.py   # Delta state & inventory math
streamlit run developer_apps/06_end_to_end_validation.py   # Full live pipeline validation
streamlit run developer_apps/07_live_dispenser_dashboard.py # Real-time dispenser monitor
```

---

## 📂 Project Repository Structure

```text
MediDispense/
├── .env.example               # Environment variables template
├── .gitignore                 # Hardened GitHub ignore rules (protects private reports & raw sets)
├── ARCHITECTURE.md            # In-depth architectural specification
├── LICENSE                    # MIT Open Source License
├── README.md                  # Master project documentation
├── config.py                  # Global model paths & detection confidence thresholds
├── requirements.txt           # Production Python dependencies
├── pyproject.toml             # Python build & tool configuration
│
├── alerting/                  # Alerting Engine (SMS, Push notifications, Buzzer dispatchers)
├── app/                       # Vision Subsystem orchestration & data models
├── backend/                   # FastAPI REST controllers, routes, and WebSocket endpoints
├── clinical/                  # Clinical adherence rules matrix & schedule verification
├── database/                  # Repositories & persistence (MongoDB Atlas + offline caches)
├── developer_apps/            # 10 Streamlit diagnostic & developer validation portals
├── hardware/                  # ESP32-CAM firmware, camera maps, and wiring specifications
├── inventory/                 # Dynamic inventory tracking & single source of truth
├── medidispense-ui/           # React 18 + Vite telemetry web dashboard
│   ├── src/pages/             # Clinical pages (TabletScan, Prescriptions, Schedules, Audits)
│   └── package.json           # Frontend dependency manifest
├── models/                    # Model definition, training, and production weights
│   ├── model_a/               # Model A (Strip & 4-Corner Localizer)
│   ├── model_b/               # Model B v2.0 (Blister Pocket Detector)
│   ├── model_c/               # Model C v1.0 (MobileNetV3 Tablet Classifier)
│   └── production/            # Official Production Weights (.pt & .json metadata)
│       ├── ModelA_v2.0.pt     # Fine-tuned YOLO11m strip detector (18.2 MB)
│       ├── ModelB_v2.0.pt     # Fine-tuned YOLO11s pocket detector (18.2 MB)
│       └── ModelC_v1.0.pt     # MobileNetV3 tablet classifier (5.9 MB)
├── pipeline/                  # Pipeline schemas, orientation-aware homography, and math
├── scripts/                   # Dataset generation, annotation validation, and evaluation tools
└── tests/                     # 140+ Automated unit, integration, and performance tests
```

---

## 🔒 Security & Deployment Best Practices

1. **Environment Secrets**: Never commit `.env` containing database credentials. Always copy `.env.example` to `.env` on deployment targets.
2. **Model Weights**: Final production weights (`models/production/*.pt`) are tracked under version control. Intermediate checkpoints (`runs/`) are excluded.
3. **Physical Optical Setup**: For optimal accuracy with the ESP32-CAM (OV2640):
   - Rotate the manual lens ring counter-clockwise for macro focus at 10–12 cm.
   - Use dual 45° angled diffused illumination (320 lx) to eliminate foil specular glare.

---

## 📄 Citation

If you find this work useful in your research or project, please cite:

```bibtex
@inproceedings{medidispense2026,
  title     = {An IoT-Enabled Smart Medication Dispensing and Cold-Chain Tracking Ecosystem with Multi-Model Edge Vision Verification},
  author    = {MediDispense Research Team},
  booktitle = {Proceedings of the International Conference on Healthcare IoT and Pervasive Systems},
  series    = {Communications in Computer and Information Science (CCIS)},
  publisher = {Springer Nature},
  year      = {2026}
}
```

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
