import sys
from pathlib import Path
import cv2

ROOT = Path(__file__).parent.parent
sys.path.append(str(ROOT))

from ultralytics import YOLO
from config import MODEL_B_PATH, CONF_MODEL_B

def predict_pockets(image_path, conf=CONF_MODEL_B):
    img_path = Path(image_path)
    if not img_path.exists():
        print(f"Error: Image not found at {image_path}")
        return

    if not MODEL_B_PATH.exists():
        print(f"Error: Model B weights not found at {MODEL_B_PATH}")
        return

    img = cv2.imread(str(img_path))
    if img is None:
        print(f"Failed to load image {image_path}")
        return

    model = YOLO(str(MODEL_B_PATH))
    results = list(model(str(img_path), conf=conf))
    boxes = results[0].boxes if (results and hasattr(results[0], 'boxes') and results[0].boxes is not None) else []

    print(f"\n=== Model B (Pocket Detector) Results ===")
    print(f"Image: {image_path}")
    print(f"Total Pockets Detected: {len(boxes)} (conf_threshold={conf})")

    annotated = img.copy()

    for i, box in enumerate(boxes, 1):
        x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
        c = box.conf[0].item()
        print(f"  Pocket {i:02d}: Box=({x1}, {y1}, {x2}, {y2}) | Confidence={c:.4f}")

        # Draw green bounding box
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
        label = f"pocket {c:.2f}"
        cv2.putText(annotated, label, (x1, max(15, y1 - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

    # Save annotated image
    out_dir = ROOT / "runs" / "detect"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"model_b_{img_path.name}"
    cv2.imwrite(str(out_path), annotated)
    print(f"\nSaved annotated image to: {out_path}")

    # Display pop-up window
    window_name = f"Model B Pocket Detection - {img_path.name}"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.imshow(window_name, annotated)
    print("Press any key to close the window...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python models/model_b/predict.py <image_path>")

        sys.exit(1)
        
    predict_pockets(sys.argv[1])
