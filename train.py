"""
YOLO11 training pipeline for Blister Strip Detector.

Usage:
    python train.py
    python train.py --epochs 100 --batch 16 --imgsz 640
    python train.py --resume
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

PROJECT_ROOT = Path(__file__).resolve().parent
DATASET_DIR = PROJECT_ROOT / "dataset"
DATA_YAML = DATASET_DIR / "data.yaml"
DEFAULT_EPOCHS = 200
DEFAULT_BATCH = 16
DEFAULT_IMGSZ = 640
DEFAULT_PATIENCE = 50
DEFAULT_WORKERS = 4
DEFAULT_LR = 0.01
DEFAULT_MODEL = "yolo11s.pt"
DEFAULT_SEED = 42
DEFAULT_DEGREES = 20.0
DEFAULT_MOSAIC = 0.0
DEFAULT_FLIPLR = 0.5
DEFAULT_FLIPUD = 0.0



def validate_labels(data_yaml: Path) -> None:
    """Verify every image has a matching label file. Exit on inconsistencies."""
    import yaml
    with open(data_yaml) as f:
        cfg = yaml.safe_load(f)

    data_root = Path(cfg.get("path", ""))
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
        missing_images = label_stems - image_stems
        empty_labels = [p for p in labels if p.stat().st_size == 0]

        log.info("Split '%s': %d images, %d labels, %d matched",
                 split, len(images), len(labels), len(matched))

        if missing_labels:
            log.warning("  -> %d image(s) missing labels (e.g. %s)",
                        len(missing_labels), list(missing_labels)[:3])
            ok = False
        if missing_images:
            log.warning("  -> %d label(s) missing images (e.g. %s)",
                        len(missing_images), list(missing_images)[:3])
            ok = False
        if empty_labels:
            log.warning("  -> %d empty label file(s): %s",
                        len(empty_labels), [p.name for p in empty_labels[:5]])
            ok = False

    if not ok:
        log.error("Dataset has inconsistencies. Fix them before training.")
        sys.exit(1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train YOLO11 Blister Strip Detector")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL,
                        help=f"Model variant (default: {DEFAULT_MODEL})")
    parser.add_argument("--data", type=str, default=str(DATA_YAML),
                        help="Path to data.yaml")
    parser.add_argument("--epochs", type=int, default=DEFAULT_EPOCHS,
                        help="Number of training epochs")
    parser.add_argument("--batch", type=int, default=DEFAULT_BATCH,
                        help="Batch size")
    parser.add_argument("--imgsz", type=int, default=DEFAULT_IMGSZ,
                        help="Input image size")
    parser.add_argument("--patience", type=int, default=DEFAULT_PATIENCE,
                        help="Early stopping patience")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS,
                        help="Dataloader workers")
    parser.add_argument("--lr", type=float, default=DEFAULT_LR,
                        help="Initial learning rate")
    parser.add_argument("--device", type=str, default="",
                        help="Device (cuda:0, cpu, or empty for auto)")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from last checkpoint")
    parser.add_argument("--project", type=str, default=str(PROJECT_ROOT / "runs"),
                        help="Project directory")
    parser.add_argument("--name", type=str, default="train",
                        help="Experiment name")
    parser.add_argument("--exist-ok", action="store_true",
                        help="Overwrite existing experiment")
    parser.add_argument("--pretrained", action="store_true", default=True,
                        help="Start from pretrained weights")
    parser.add_argument("--optimizer", type=str, default="auto",
                        choices=["SGD", "Adam", "AdamW", "auto"],
                        help="Optimizer")
    parser.add_argument("--cos-lr", action="store_true", default=True,
                        help="Use cosine LR scheduler")
    parser.add_argument("--amp", action="store_true", default=True,
                        help="Use mixed precision training")
    parser.add_argument("--fraction", type=float, default=1.0,
                        help="Fraction of dataset to train on")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED,
                        help="Random seed for reproducibility")
    parser.add_argument("--deterministic", action="store_true",
                        help="Enable deterministic mode (slower but reproducible)")
    parser.add_argument("--degrees", type=float, default=DEFAULT_DEGREES,
                        help="Rotation degrees augmentation")
    parser.add_argument("--mosaic", type=float, default=DEFAULT_MOSAIC,
                        help="Mosaic augmentation ratio")
    parser.add_argument("--fliplr", type=float, default=DEFAULT_FLIPLR,
                        help="Horizontal flip ratio")
    parser.add_argument("--flipud", type=float, default=DEFAULT_FLIPUD,
                        help="Vertical flip ratio")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_path = Path(args.data)

    if not data_path.exists():
        log.error("data.yaml not found at %s", data_path)
        sys.exit(1)

    validate_labels(data_path)

    checks()

    device = args.device or ("cuda:0" if torch.cuda.is_available() else "cpu")
    log.info("Using device: %s", device)
    log.info("Training config: epochs=%d, batch=%d, imgsz=%d, patience=%d, seed=%d",
             args.epochs, args.batch, args.imgsz, args.patience, args.seed)

    model = YOLO(args.model)

    train_kwargs = dict(
        data=str(data_path),
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        patience=args.patience,
        workers=args.workers,
        device=device,
        resume=args.resume,
        project=args.project,
        name=args.name,
        exist_ok=args.exist_ok,
        pretrained=args.pretrained,
        optimizer=args.optimizer,
        cos_lr=args.cos_lr,
        amp=args.amp,
        fraction=args.fraction,
        seed=args.seed,
        degrees=args.degrees,
        mosaic=args.mosaic,
        close_mosaic=0,
        fliplr=args.fliplr,
        flipud=args.flipud,
        cache=True,
        save=True,
        val=True,
        plots=True,
    )
    if args.optimizer != "auto":
        train_kwargs["lr0"] = args.lr

    if args.resume:
        log.info("Resuming training from last checkpoint...")

    results = model.train(**train_kwargs)
    save_dir = getattr(results, "save_dir", None) or getattr(model.trainer, "save_dir", "runs/detect")
    log.info("Training complete. Results saved to %s", save_dir)



if __name__ == "__main__":
    main()

