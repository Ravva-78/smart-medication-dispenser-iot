"""
Evaluate trained YOLO11 blister strip detector.

Usage:
    python models/model_a/evaluate.py
    python models/model_a/evaluate.py --weights models/production/ModelA_v1.0.pt
    python models/model_a/evaluate.py --split test
"""


import argparse
import json
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
DATA_YAML = PROJECT_ROOT / "dataset" / "data.yaml"
DEFAULT_WEIGHTS = PROJECT_ROOT.parent.parent / "models" / "production" / "ModelA_v1.0.pt"
if not DEFAULT_WEIGHTS.exists():
    DEFAULT_WEIGHTS = PROJECT_ROOT / "runs" / "train-6" / "weights" / "best.pt"

METRICS_FILE = "evaluation_metrics.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate YOLO11 Blister Strip Detector")
    parser.add_argument("--weights", type=str, default=str(DEFAULT_WEIGHTS),
                        help="Path to model weights")
    parser.add_argument("--data", type=str, default=str(DATA_YAML),
                        help="Path to data.yaml")
    parser.add_argument("--split", type=str, default="val",
                        choices=["val", "test"], help="Dataset split to evaluate on")
    parser.add_argument("--imgsz", type=int, default=640,
                        help="Input image size")
    parser.add_argument("--batch", type=int, default=16,
                        help="Batch size")
    parser.add_argument("--device", type=str, default="",
                        help="Device (cuda:0, cpu, or empty for auto)")
    parser.add_argument("--conf", type=float, default=0.25,
                        help="Confidence threshold")
    parser.add_argument("--iou", type=float, default=0.45,
                        help="IoU threshold for NMS")
    parser.add_argument("--save-json", action="store_true", default=True,
                        help="Save metrics to JSON")
    parser.add_argument("--plots", action="store_true", default=True,
                        help="Generate evaluation plots")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    weights_path = Path(args.weights)

    if not weights_path.exists():
        log.error("Weights not found at %s", weights_path)
        log.error("Train a model first with: python train.py")
        sys.exit(1)

    if not Path(args.data).exists():
        log.error("data.yaml not found at %s", args.data)
        sys.exit(1)

    log.info("Loading model: %s", weights_path)
    model = YOLO(str(weights_path))

    log.info("Evaluating on %s split...", args.split)
    metrics = model.val(
        data=args.data,
        split=args.split,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device or None,
        conf=args.conf,
        iou=args.iou,
        plots=args.plots,
        save_json=args.save_json,
    )

    log.info("=" * 50)
    log.info("Evaluation Results")
    log.info("=" * 50)
    log.info("Precision:      %.4f", metrics.box.p[0])
    log.info("Recall:         %.4f", metrics.box.r[0])
    log.info("mAP50:          %.4f", metrics.box.map50)
    log.info("mAP50-95:       %.4f", metrics.box.map)
    log.info("F1-score:       %.4f", metrics.box.f1[0])
    log.info("=" * 50)

    results = {
        "split": args.split,
        "precision": float(metrics.box.p[0]),
        "recall": float(metrics.box.r[0]),
        "map50": float(metrics.box.map50),
        "map50_95": float(metrics.box.map),
        "f1_score": float(metrics.box.f1[0]),
        "model": str(weights_path),
    }

    metrics_path = Path(metrics.save_dir) / METRICS_FILE
    with open(metrics_path, "w") as f:
        json.dump(results, f, indent=2)
    log.info("Metrics saved to: %s", metrics_path)


if __name__ == "__main__":
    main()
