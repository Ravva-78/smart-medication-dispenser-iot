import cv2
from pathlib import Path


def extract_pockets(image, boxes, output_dir=None, prefix="", save=False):
    """
    Extract pocket crops from an image given bounding boxes.
    
    Args:
        image: numpy array (BGR) or path to image
        boxes: list of (x1, y1, x2, y2) in pixel coords, or list of (xc, yc, w, h) normalized
               OR list of ultralytics Results boxes
        output_dir: directory to save crops (only used if save=True)
        prefix: optional filename prefix
        save: if True, write crops to disk; if False, return in RAM only
    Returns:
        list of (filename, crop_image, (x1, y1, x2, y2))
    """
    if isinstance(image, str) or isinstance(image, Path):
        img = cv2.imread(str(image))
        if img is None:
            raise ValueError(f"Failed to load image: {image}")
    else:
        img = image.copy()

    h, w = img.shape[:2]
    if save and output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

    crops = []
    for i, box in enumerate(boxes, 1):
        if hasattr(box, 'xyxy'):  # ultralytics Results
            x1, y1, x2, y2 = map(int, box.xyxy[0])
        elif len(box) == 4:
            if max(box) <= 1.0:  # normalized (xc, yc, bw, bh) YOLO format
                xc, yc, bw, bh = box
                x1 = int((xc - bw / 2) * w)
                y1 = int((yc - bh / 2) * h)
                x2 = int((xc + bw / 2) * w)
                y2 = int((yc + bh / 2) * h)
            else:  # pixel (x1, y1, x2, y2)
                x1, y1, x2, y2 = map(int, box)

        elif len(box) == 5:  # class + normalized (xc, yc, bw, bh)
            _, xc, yc, bw, bh = box
            x1 = int((xc - bw / 2) * w)
            y1 = int((yc - bh / 2) * h)
            x2 = int((xc + bw / 2) * w)
            y2 = int((yc + bh / 2) * h)
        else:
            continue

        # Apply 5% expansion padding for extra context tolerance
        box_w, box_h = x2 - x1, y2 - y1
        pad_x = int(box_w * 0.05)
        pad_y = int(box_h * 0.05)

        x1 = max(0, x1 - pad_x)
        y1 = max(0, y1 - pad_y)
        x2 = min(w, x2 + pad_x)
        y2 = min(h, y2 + pad_y)

        crop = img[y1:y2, x1:x2]

        if crop.size == 0 or crop.shape[0] < 5 or crop.shape[1] < 5:
            continue

        filename = f"{prefix}pocket_{i:03d}.jpg"

        if save and output_dir:
            out_dir = Path(output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(out_dir / filename), crop)

        crops.append((filename, crop, (x1, y1, x2, y2)))

    return crops


def extract_from_labels(images_dir, labels_dir, output_dir):
    """Extract from YOLO .txt label files and save to disk (for training data generation)."""
    img_dir = Path(images_dir)
    lbl_dir = Path(labels_dir)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    
    images = sorted([f for f in img_dir.iterdir() if f.suffix.lower() in ('.jpg', '.jpeg', '.png')])
    for img_path in images:
        stem = img_path.stem
        label_path = lbl_dir / f"{stem}.txt"
        if not label_path.exists():
            continue
        boxes = []
        with open(label_path) as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) == 5:
                    boxes.append(list(map(float, parts)))
        if boxes:
            extract_pockets(img_path, boxes, output_dir=out, prefix=f"{stem}_", save=True)



def extract_from_predictions(image_path, results, output_dir):
    """Extract from YOLO prediction results (for inference)."""
    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError(f"Failed to load: {image_path}")
    boxes = results[0].boxes if hasattr(results[0], 'boxes') else results
    return extract_pockets(img, boxes, output_dir)


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent.parent.parent
    extract_from_labels(
        root / "models" / "model_b" / "dataset" / "images" / "train",
        root / "models" / "model_b" / "dataset" / "labels" / "train",
        root / "models" / "model_c" / "raw_crops" / "train"
    )

