import cv2
import os
from pathlib import Path

CROPS_DIR = Path(__file__).parent.parent / "dataset" / "raw_crops"
TRAIN_DIR = Path(__file__).parent.parent / "dataset"
WINDOW_NAME = "Model C - Sort Crops (P=present M=missing N=next Q=quit)"
IMG_SIZE = 300

images = sorted(CROPS_DIR.glob("*.jpg"))
idx = 0
stats = {"classified": 0, "present": 0, "missing": 0, "skipped": 0}

cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
cv2.resizeWindow(WINDOW_NAME, IMG_SIZE + 100, IMG_SIZE + 100)

while 0 <= idx < len(images):
    path = images[idx]
    img = cv2.imread(str(path))
    if img is None:
        idx += 1
        continue

    h, w = img.shape[:2]
    scale = min(IMG_SIZE / w, IMG_SIZE / h)
    display = cv2.resize(img, (int(w * scale), int(h * scale)))
    info = f"[{idx+1}/{len(images)}] {path.name}"
    cv2.putText(display, info, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    cv2.imshow(WINDOW_NAME, display)

    key = cv2.waitKey(0) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('p'):
        dest = TRAIN_DIR / "present" / path.name
        os.rename(str(path), str(dest))
        stats["present"] += 1
        stats["classified"] += 1
        idx += 1
    elif key == ord('m'):
        dest = TRAIN_DIR / "missing" / path.name
        os.rename(str(path), str(dest))
        stats["missing"] += 1
        stats["classified"] += 1
        idx += 1
    elif key == ord('n'):
        stats["skipped"] += 1
        idx += 1
    elif key == ord('b') or key == 8:
        idx = max(0, idx - 1)

cv2.destroyAllWindows()
print(f"\nDone. Classified: {stats['classified']} | Present: {stats['present']} | Missing: {stats['missing']} | Skipped: {stats['skipped']}")
