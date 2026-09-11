"""
Export trained YOLO11 model to deployment formats.

Supported formats: ONNX, TorchScript, TensorRT.

Usage:
    python models/model_a/export_model.py
    python models/model_a/export_model.py --format onnx
    python models/model_a/export_model.py --format all
    python models/model_a/export_model.py --weights models/production/ModelA_v1.0.pt
"""


import argparse
import logging
import sys
from pathlib import Path

from ultralytics import YOLO

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_WEIGHTS = PROJECT_ROOT.parent.parent / "models" / "production" / "ModelA_v1.0.pt"
if not DEFAULT_WEIGHTS.exists():
    DEFAULT_WEIGHTS = PROJECT_ROOT / "runs" / "train-6" / "weights" / "best.pt"

EXPORT_DIR = PROJECT_ROOT / "exports"

SUPPORTED_FORMATS = {
    "onnx": {"onnx": True, "opset": 12},
    "torchscript": {"torchscript": True},
    "tensorrt": {"engine": True, "half": True, "imgsz": 640},
    "all": None,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export YOLO11 model to deployment formats")
    parser.add_argument("--weights", "-w", type=str, default=str(DEFAULT_WEIGHTS),
                        help="Path to model weights")
    parser.add_argument("--format", "-f", type=str, default="onnx",
                        choices=list(SUPPORTED_FORMATS),
                        help="Export format")
    parser.add_argument("--imgsz", type=int, default=640,
                        help="Input image size for exported model")
    parser.add_argument("--half", action="store_true", default=False,
                        help="FP16 quantization (ONNX/TensorRT)")
    parser.add_argument("--device", type=str, default="cpu",
                        help="Device for export (cpu, cuda:0)")
    parser.add_argument("--output", "-o", type=str, default=str(EXPORT_DIR),
                        help="Output directory")
    return parser.parse_args()


def export_single(model: YOLO, fmt: str, kwargs: dict, output_dir: Path) -> Path | None:
    """Export to a single format and return the output path."""
    log.info("Exporting to %s ...", fmt.upper())
    try:
        out = model.export(**kwargs)
        out_path = Path(out)
        log.info("  -> Exported: %s", out_path)
        return out_path
    except Exception as e:
        log.error("  -> Export to %s failed: %s", fmt.upper(), e)
        return None


def main() -> None:
    args = parse_args()
    weights_path = Path(args.weights)

    if not weights_path.exists():
        log.error("Weights not found at %s", weights_path)
        log.error("Train a model first with: python train.py")
        sys.exit(1)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    log.info("Loading model: %s", weights_path)
    model = YOLO(str(weights_path))

    if args.format == "all":
        formats_to_export = [f for f in SUPPORTED_FORMATS if f != "all"]
    else:
        formats_to_export = [args.format]

    exported = []

    for fmt in formats_to_export:
        config = dict(SUPPORTED_FORMATS.get(fmt) or {})
        config["imgsz"] = args.imgsz
        config["half"] = args.half if fmt in ("onnx", "tensorrt") else False
        config["device"] = args.device

        result = export_single(model, fmt, config, output_dir)
        if result:
            exported.append(result)

    if exported:
        log.info("=" * 50)
        log.info("Export complete. %d format(s) saved.", len(exported))
        for p in exported:
            log.info("  %s", p)
    else:
        log.error("No exports succeeded.")
        sys.exit(1)


if __name__ == "__main__":
    main()
