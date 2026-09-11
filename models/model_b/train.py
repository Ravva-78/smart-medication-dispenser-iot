"""
YOLO11 training script for Model B (Blister Pocket Detector).

Usage:
    python models/model_b/train.py
"""


import argparse
import logging
import sys
from pathlib import Path
import torch
from ultralytics import YOLO, checks

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

MODEL_B_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODEL_B_DIR.parent.parent
DATA_YAML = MODEL_B_DIR / "dataset" / "data.yaml"


DEFAULT_EPOCHS = 200
DEFAULT_BATCH = 16
DEFAULT_IMGSZ = 640
DEFAULT_PATIENCE = 50


DEFAULT_WORKERS = 0
DEFAULT_MODEL = "yolo11s.pt"
DEFAULT_SEED = 42




def validate_labels(data_yaml: Path) -> None:
    """Verify every image has a matching label file."""
    import yaml
    with open(data_yaml) as f:
        cfg = yaml.safe_load(f)

    data_root = MODEL_B_DIR / "dataset"

    ok = True
    for split in ["train", "val", "test"]:
        img_dir = data_root / cfg.get(split, f"images/{split}")
        lbl_dir = data_root / "labels" / split

        if not img_dir.exists():
            continue

        images = sorted(img_dir.glob("*.*"))
        labels = sorted(lbl_dir.glob("*.txt")) if lbl_dir.exists() else []
        image_stems = {p.stem for p in images}
        label_stems = {p.stem for p in labels}

        matched = image_stems & label_stems
        missing_labels = image_stems - label_stems
        empty_labels = [p for p in labels if p.stat().st_size == 0]

        log.info("Model B Split '%s': %d images, %d labels, %d matched",
                 split, len(images), len(labels), len(matched))

        if missing_labels:
            log.warning("  -> %d image(s) missing labels (e.g. %s)",
                        len(missing_labels), list(missing_labels)[:3])
            ok = False
        if empty_labels:
            log.warning("  -> %d empty label file(s): %s",
                        len(empty_labels), [p.name for p in empty_labels[:5]])
            ok = False

    if not ok:
        log.error("Dataset has missing/empty labels. Complete annotation before training.")
        sys.exit(1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train YOLO11 Model B (Pocket Detector)")
    parser.add_argument("--model", type=str, default=str(MODEL_B_DIR / DEFAULT_MODEL),
                        help="Model checkpoint or pretrained weights")
    parser.add_argument("--epochs", type=int, default=DEFAULT_EPOCHS,
                        help="Number of training epochs")
    parser.add_argument("--batch", type=int, default=DEFAULT_BATCH,
                        help="Batch size")
    parser.add_argument("--imgsz", type=int, default=DEFAULT_IMGSZ,
                        help="Image size")
    parser.add_argument("--patience", type=int, default=DEFAULT_PATIENCE,
                        help="Early stopping patience")
    parser.add_argument("--device", type=str, default="",
                        help="Device to use (e.g. cuda:0, cpu)")
    parser.add_argument("--name", type=str, default="modelb_train",
                        help="Run name")
    parser.add_argument("--resume", action="store_true",
                        help="Resume training")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_path = DATA_YAML
    if not data_path.exists():
        log.error("data.yaml not found at %s", data_path)
        sys.exit(1)

    validate_labels(data_path)
    checks()

    device = args.device or ("cuda:0" if torch.cuda.is_available() else "cpu")
    log.info("Using device: %s", device)
    log.info("Training config: epochs=%d, batch=%d, imgsz=%d, patience=%d",
             args.epochs, args.batch, args.imgsz, args.patience)

    model = YOLO(args.model)

    train_kwargs = dict(
        data=str(data_path),
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        patience=args.patience,
        workers=DEFAULT_WORKERS,
        device=device,
        project=str(MODEL_B_DIR / "runs"),
        name=args.name,
        pretrained=True,
        optimizer="auto",
        cos_lr=True,
        amp=True,
        seed=DEFAULT_SEED,
        degrees=15.0,
        mosaic=0.0,
        close_mosaic=0,
        fliplr=0.5,
        flipud=0.0,
        exist_ok=True,
        cache=True,
        save=True,
        val=True,
        plots=True,
        resume=args.resume,
    )

    results = model.train(**train_kwargs)
    save_dir = getattr(results, "save_dir", None) or getattr(model.trainer, "save_dir", "runs/detect")
    log.info("Model B (Pocket Detector) training complete. Saved to %s", save_dir)

if __name__ == "__main__":
    main()

