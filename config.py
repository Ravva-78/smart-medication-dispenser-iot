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

# --- Perspective correction ---
PERSPECTIVE_ENABLED = True
PERSPECTIVE_WIDTH = 800
PERSPECTIVE_HEIGHT = 600
