from ultralytics import YOLO
from pathlib import Path
import cv2
import json

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = PROJECT_ROOT / "runs" / "train-6" / "weights" / "best.pt"
SRC_DIR = PROJECT_ROOT / "dataset" / "images"
DST_DIR = PROJECT_ROOT / "Model_B" / "modelB_dataset"
REPORT_PATH = PROJECT_ROOT / "Model_B" / "crop_report.json"


DST_DIR.mkdir(parents=True, exist_ok=True)

model = YOLO(MODEL_PATH)

# Collect all source images
src_images = []
for ext in ('*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG'):
    src_images.extend(SRC_DIR.rglob(ext))

print(f"Found {len(src_images)} source images")

report = {
    "total_images": len(src_images),
    "successful_crops": [],
    "failed_detections": [],
    "low_confidence": []
}

conf_threshold = 0.3
padding_pct = 0.08  # 8% padding

for img_path in src_images:
    results = model(img_path, verbose=False)
    
    if len(results[0].boxes) == 0:
        report["failed_detections"].append(str(img_path.name))
        continue
    
    # Get highest confidence detection
    boxes = results[0].boxes
    confs = boxes.conf.cpu().numpy()
    best_idx = confs.argmax()
    best_conf = float(confs[best_idx])
    
    if best_conf < conf_threshold:
        report["low_confidence"].append({"file": str(img_path.name), "conf": best_conf})
        continue
    
    # Get bounding box (xyxy format)
    x1, y1, x2, y2 = boxes.xyxy[best_idx].cpu().numpy()
    x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])
    
    # Add padding
    h, w = x2 - x1, y2 - y1
    pad_x = int(w * padding_pct)
    pad_y = int(h * padding_pct)
    
    # Load image to get dimensions
    img = cv2.imread(str(img_path))
    if img is None:
        report["failed_detections"].append(str(img_path.name))
        continue
    
    img_h, img_w = img.shape[:2]
    
    # Apply padding with bounds checking
    x1 = max(0, x1 - pad_x)
    y1 = max(0, y1 - pad_y)
    x2 = min(img_w, x2 + pad_x)
    y2 = min(img_h, y2 + pad_y)
    
    # Crop
    crop = img[y1:y2, x1:x2]
    
    # Save crop
    out_name = f"strip_{img_path.stem}.jpg"
    out_path = DST_DIR / out_name
    cv2.imwrite(str(out_path), crop)
    
    report["successful_crops"].append({
        "source": str(img_path.name),
        "crop": out_name,
        "confidence": best_conf,
        "bbox": [int(x1), int(y1), int(x2), int(y2)]
    })

# Save report
with open(REPORT_PATH, 'w') as f:
    json.dump(report, f, indent=2)

print(f"\n=== CROP REPORT ===")
print(f"Total images: {report['total_images']}")
print(f"Successful crops: {len(report['successful_crops'])}")
print(f"Failed detections: {len(report['failed_detections'])}")
print(f"Low confidence (<{conf_threshold}): {len(report['low_confidence'])}")
print(f"\nReport saved to: {REPORT_PATH}")
print(f"Crops saved to: {DST_DIR}")