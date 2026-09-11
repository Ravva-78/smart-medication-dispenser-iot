import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from app.detect_image import parse_args, log, YOLO, cv2, PROJECT_ROOT, OUTPUT_DIR, CLASS_NAME, COLORS

def main() -> None:
    args = parse_args()

    source_path = Path(args.source)
    if not source_path.exists():
        log.error("Source image not found: %s", source_path)
        sys.exit(1)

    weights_path = Path(args.weights)
    if not weights_path.exists():
        log.error("Model weights not found: %s", weights_path)
        sys.exit(1)

    log.info("Running inference on: %s", source_path)

    model = YOLO(str(weights_path))

    results = model.predict(
        source=str(source_path),
        conf=args.conf,
        iou=args.iou,
        imgsz=args.imgsz,
        device=args.device if args.device else None,
        verbose=True,
    )

    img = cv2.imread(str(source_path))
    if img is None:
        log.error("Failed to read image: %s", source_path)
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rois_dir = OUTPUT_DIR / "rois"

    det_count = 0
    for result in results:
        boxes = getattr(result, "boxes", None)
        if boxes is None or len(boxes) == 0:
            log.warning("No %s detected in the image.", CLASS_NAME)
            continue

        for i, box in enumerate(boxes):
            conf = float(box.conf[0])
            xyxy = box.xyxy[0].cpu().numpy().astype(int)
            x1, y1, x2, y2 = xyxy

            log.info("Detected %s with confidence: %.4f", CLASS_NAME, conf)

            cv2.rectangle(img, (x1, y1), (x2, y2), COLORS["box"], 2)
            label = f"{CLASS_NAME} {conf:.2f}"
            (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
            cv2.rectangle(img, (x1, y1 - h - 10), (x1 + w + 10, y1), COLORS["label_bg"], -1)
            cv2.putText(img, label, (x1 + 5, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLORS["text"], 1, cv2.LINE_AA)

            crop = img[y1:y2, x1:x2]
            if crop.size > 0:
                rois_dir.mkdir(parents=True, exist_ok=True)
                roi_path = rois_dir / f"{source_path.stem}_roi_{i+1}.jpg" if len(boxes) > 1 else rois_dir / f"{source_path.stem}_roi.jpg"
                cv2.imwrite(str(roi_path), crop)
                log.info("ROI saved: %s", roi_path)

            det_count += 1

    annotated_path = OUTPUT_DIR / f"{source_path.stem}_annotated.jpg"
    cv2.imwrite(str(annotated_path), img)
    log.info("Annotated image saved: %s", annotated_path)

    if not args.no_show:
        window_name = "Blister Strip Detection"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.imshow(window_name, img)
        log.info("Press any key to close the window...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
