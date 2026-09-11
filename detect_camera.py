"""
Real-time blister strip detection via webcam.

Usage:
    python detect_camera.py
    python detect_camera.py --conf 0.5 --camera 0
"""

import argparse
import logging
import time
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
DEFAULT_WEIGHTS = PROJECT_ROOT / "runs" / "train" / "weights" / "best.pt"
ROI_DIR = PROJECT_ROOT / "runs" / "detect" / "camera_rois"
CLASS_NAME = "blister_strip"
COLORS = {
    "box": (0, 255, 0),
    "label_bg": (0, 200, 0),
    "text": (255, 255, 255),
    "fps": (0, 255, 255),
    "info_bg": (0, 0, 0),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Real-time blister strip detection via webcam")
    parser.add_argument("--weights", "-w", type=str, default=str(DEFAULT_WEIGHTS),
                        help="Path to model weights")
    parser.add_argument("--camera", type=int, default=0,
                        help="Camera device ID")
    parser.add_argument("--conf", type=float, default=0.25,
                        help="Confidence threshold")
    parser.add_argument("--iou", type=float, default=0.45,
                        help="IoU threshold for NMS")
    parser.add_argument("--imgsz", type=int, default=640,
                        help="Input image size")
    parser.add_argument("--device", type=str, default="",
                        help="Device (cuda:0, cpu, or empty for auto)")
    parser.add_argument("--save-roi", action="store_true", default=True,
                        help="Save cropped blister strip ROIs")
    parser.add_argument("--roi-conf", type=float, default=0.7,
                        help="Minimum confidence to save ROI")
    parser.add_argument("--resolution", type=str, default="640x480",
                        help="Camera resolution (width x height)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    weights_path = Path(args.weights)

    if not weights_path.exists():
        log.error("Model weights not found at %s", weights_path)
        log.error("Train a model first with: python train.py")
        return

    model = YOLO(str(weights_path))

    res_w, res_h = map(int, args.resolution.split("x"))
    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        log.error("Could not open camera %d", args.camera)
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, res_w)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, res_h)

    roi_dir = ROI_DIR
    if args.save_roi:
        roi_dir.mkdir(parents=True, exist_ok=True)

    roi_counter = 0
    prev_time = time.perf_counter()
    fps = 0.0

    log.info("Starting camera inference. Press Q to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            log.warning("Failed to grab frame")
            break

        current_time = time.perf_counter()
        fps = 1.0 / (current_time - prev_time)
        prev_time = current_time

        results = model(
            source=frame,
            conf=args.conf,
            iou=args.iou,
            imgsz=args.imgsz,
            device=args.device or None,
            verbose=False,
        )[0]

        annotated = results.plot()

        for box_data in results.boxes:
            conf = float(box_data.conf[0])
            if args.save_roi and conf >= args.roi_conf:
                x1, y1, x2, y2 = map(int, box_data.xyxy[0].tolist())
                roi = frame[y1:y2, x1:x2]
                if roi.size > 0:
                    roi_counter += 1
                    roi_path = roi_dir / f"roi_{roi_counter:04d}.jpg"
                    cv2.imwrite(str(roi_path), roi)

        cv2.putText(annotated, f"FPS: {fps:.1f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, COLORS["fps"], 2)
        cv2.putText(annotated, f"ROIs saved: {roi_counter}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLORS["fps"], 2)

        cv2.imshow("Blister Strip Detection - Press Q to quit", annotated)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            log.info("Quit signal received")
            break

    cap.release()
    cv2.destroyAllWindows()
    log.info("Camera stopped. ROIs saved: %d", roi_counter)


if __name__ == "__main__":
    main()
