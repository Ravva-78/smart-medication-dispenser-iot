import os
from pathlib import Path

ROOT = Path(__file__).parent

PIPELINE_VERSION = "0.1.0"
SOFTWARE_VERSION = "0.1.0"


# --- Model paths ---
MODEL_A_PATH = ROOT / "models" / "production" / "ModelA_v2.0.pt"
MODEL_B_PATH = ROOT / "models" / "production" / "ModelB_v2.0.pt"
MODEL_C_PATH = ROOT / "models" / "production" / "ModelC_v1.0.pt"




# --- Inference settings ---
CONF_MODEL_A = 0.35
CONF_MODEL_B = 0.20
CONF_MODEL_C = 0.50







MODEL_C_IMG_SIZE = 224

# --- Debug logging ---
DEBUG_DIR = ROOT / "output"
SAVE_STAGE_IMAGES = False

# --- Expected blister layout (rows, cols), orientation-agnostic. Off by default: the grid is detected from the
# image. Set only when a prescription/blister really has a known layout, e.g. EXPECTED_LAYOUT=5x3 in the environment.
from pipeline.layout import parse_layout
try:
    EXPECTED_LAYOUT = parse_layout(os.getenv("EXPECTED_LAYOUT"))
except ValueError:
    EXPECTED_LAYOUT = None

# --- Per-pocket confidence floor: a pocket classified below this makes the inspection REVIEW_REQUIRED.
# Reuses InventoryManager's existing LOW_CONFIDENCE threshold (0.60) rather than a new tuned value;
# see Phase 2 report for the (thin) evidence behind it. None disables the check.
MIN_POCKET_CONF = 0.60

# --- ESP32-S3-CAM (firmware serves one JPEG per GET /capture on port 80; IP is DHCP-assigned, no default) ---
ESP32_CAM_URL = os.getenv("ESP32_CAM_URL") or (
    f"http://{os.environ['ESP32_CAM_IP']}/capture" if os.getenv("ESP32_CAM_IP") else ""
)
CAMERA_CONNECT_TIMEOUT_S = 3
CAMERA_READ_TIMEOUT_S = 20  # max silent gap while the JPEG downloads; live ESP32 transfers stalled 10-15 s on a weak link


def _env_number(name, default, cast):
    try:
        return cast(os.getenv(name, default))
    except (TypeError, ValueError):
        return cast(default)


CAMERA_RETRIES = _env_number("CAMERA_RETRIES", 2, int)             # extra capture attempts (GET only, never writes); 0 = old behaviour
CAMERA_DEADLINE_S = _env_number("CAMERA_DEADLINE_S", 45, float)    # total time budget for one capture including retries
CAMERA_RETRY_BACKOFF_S = 0.5

# --- Speed flags (set to 0 to restore the previous behaviour) ---
OCR_USE_GPU = os.getenv("OCR_USE_GPU", "1") != "0"          # EasyOCR on the GPU when CUDA is available (falls back to CPU)
WARMUP_ON_START = os.getenv("WARMUP_ON_START", "1") != "0"  # backend loads models and warms them up in the background at start

# --- Perspective correction ---
PERSPECTIVE_ENABLED = True
PERSPECTIVE_WIDTH = 800
PERSPECTIVE_HEIGHT = 600
