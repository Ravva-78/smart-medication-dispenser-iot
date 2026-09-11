"""
Run YOLO11 inference on a single image.

Saves annotated image + cropped blister strip ROI.

Usage:
    python detect_image.py --source path/to/image.jpg
    python detect_image.py --source path/to/image.jpg --conf 0.5
"""

import argparse
import logging
import sys
from pathlib import Path

import cv2
from ultralytics import YOLO

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_WEIGHTS = PROJECT_ROOT / "models" / "production" / "ModelA_v1.0.pt"
OUTPUT_DIR = PROJECT_ROOT / "runs" / "detect"
CLASS_NAME = "blister_strip"
COLORS = {
    "box": (0, 255, 0),
    "label_bg": (0, 200, 0),
    "text": (255, 255, 255),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Detect blister strips in an image")
    parser.add_argument("--source", "-s", type=str, required=True,
                        help="Path to input image")
    parser.add_argument("--weights", "-w", type=str, default=str(DEFAULT_WEIGHTS),
                        help="Path to model weights")
    parser.add_argument("--conf", type=float, default=0.50,
                        help="Confidence threshold")

    parser.add_argument("--iou", type=float, default=0.45,
                        help="IoU threshold for NMS")
    parser.add_argument("--imgsz", type=int, default=640,
                        help="Input image size")
    parser.add_argument("--device", type=str, default="",
                        help="Device (cuda:0, cpu, or empty for auto)")
    parser.add_argument("--output", "-o", type=str, default="",
                        help="Output directory (default: runs/detect/exp)")
    parser.add_argument("--save-roi", action="store_true", default=True,
                        help="Save cropped blister strip ROI")
    parser.add_argument("--no-show", action="store_true",
                        help="Do not display the result window")
    return parser.parse_args()


def draw_detection(image, box, conf: float) -> None:
    """Draw bounding box and label on the image (in-place)."""
    x1, y1, x2, y2 = map(int, box)
    label = f"{CLASS_NAME} {conf:.2f}"

    cv2.rectangle(image, (x1, y1), (x2, y2), COLORS["box"], 2)

    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
    cv2.rectangle(image, (x1, y1 - th - 8), (x1 + tw + 8, y1), COLORS["label_bg"], -1)
    cv2.putText(image, label, (x1 + 4, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX,
                0.6, COLORS["text"], 2)


def main() -> None:
    args = parse_args()
    source_path = Path(args.source)

    if not source_path.exists():
        log.error("Source image not found: %s", source_path)
        sys.exit(1)

    weights_path = Path(args.weights)
    if not weights_path.exists():
        log.error("Model weights not found at %s", weights_path)
        log.error("Train a model first with: python train.py")
        sys.exit(1)

    model = YOLO(str(weights_path))

    log.info("Running inference on: %s", source_path)
    results = model(
        source=str(source_path),
        conf=args.conf,
        iou=args.iou,
        imgsz=args.imgsz,
        device=args.device or None,
    )[0]

    image = results.orig_img.copy()
    has_detection = False

    for box_data in results.boxes:
        xyxy = box_data.xyxy[0].tolist()
        conf = float(box_data.conf[0])
        draw_detection(image, xyxy, conf)
        has_detection = True
        log.info("Detected %s with confidence: %.4f", CLASS_NAME, conf)

        if args.save_roi:
            x1, y1, x2, y2 = map(int, xyxy)
            roi = results.orig_img[y1:y2, x1:x2]
            if roi.size > 0:
                stem = source_path.stem
                roi_dir = Path(args.output or OUTPUT_DIR) / "rois"
                roi_dir.mkdir(parents=True, exist_ok=True)
                roi_path = roi_dir / f"{stem}_roi.jpg"
                cv2.imwrite(str(roi_path), roi)
                log.info("ROI saved: %s", roi_path)

    if not has_detection:
        log.warning("No %s detected in the image.", CLASS_NAME)

    output_dir = Path(args.output or OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{source_path.stem}_annotated.jpg"
    cv2.imwrite(str(out_path), image)
    log.info("Annotated image saved: %s", out_path)

    if not args.no_show:
        cv2.imshow("Blister Strip Detection", image)
        log.info("Press any key to close the window...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
