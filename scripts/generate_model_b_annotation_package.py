import os
import shutil
from pathlib import Path
import cv2
import torch
from ultralytics import YOLO

def main():
    core_root = Path(__file__).resolve().parent.parent
    model_path = core_root / "models" / "production" / "ModelA_v2.0.pt"
    src_dataset = core_root / "dataset" / "images"
    target_dir = Path(r"C:\DEV\Projects\College_Projects\ProjectWork\ProjectWork\Annotation_Packages_Model_B")
    tools_dir = Path(r"C:\DEV\Projects\College_Projects\ProjectWork\ProjectWork\Annotation_Packages\tools")

    print(f"Loading Model A from: {model_path}")
    model = YOLO(str(model_path))

    splits = ["train", "val", "test"]
    padding_pct = 0.05  # 5% padding around strip

    stats = {}

    for split in splits:
        src_split_dir = src_dataset / split
        dst_img_dir = target_dir / "Person_1" / "images" / split
        dst_lbl_dir = target_dir / "Person_1" / "labels" / split

        dst_img_dir.mkdir(parents=True, exist_ok=True)
        dst_lbl_dir.mkdir(parents=True, exist_ok=True)

        images = [f for f in src_split_dir.iterdir() if f.is_file() and f.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]]
        print(f"\nProcessing [{split}] split: {len(images)} images...")

        cropped_count = 0
        fallback_count = 0

        for img_path in images:
            img = cv2.imread(str(img_path))
            if img is None:
                print(f"Warning: could not read {img_path.name}")
                continue

            h, w = img.shape[:2]
            results = model(img, conf=0.40, verbose=False, device=0 if torch.cuda.is_available() else "cpu")

            # Extract best detection
            if len(results) > 0 and hasattr(results[0], "boxes") and len(results[0].boxes) > 0:
                boxes = results[0].boxes
                best_idx = int(boxes.conf.argmax().cpu())
                x1, y1, x2, y2 = map(int, boxes.xyxy[best_idx].cpu().numpy())

                # Apply padding
                bw = x2 - x1
                bh = y2 - y1
                pad_x = int(bw * padding_pct)
                pad_y = int(bh * padding_pct)

                x1 = max(0, x1 - pad_x)
                y1 = max(0, y1 - pad_y)
                x2 = min(w, x2 + pad_x)
                y2 = min(h, y2 + pad_y)

                crop = img[y1:y2, x1:x2]
                if crop.size > 0:
                    cv2.imwrite(str(dst_img_dir / img_path.name), crop)
                    cropped_count += 1
                else:
                    cv2.imwrite(str(dst_img_dir / img_path.name), img)
                    fallback_count += 1
            else:
                # Fallback to full image
                cv2.imwrite(str(dst_img_dir / img_path.name), img)
                fallback_count += 1

        stats[split] = {"total": len(images), "cropped": cropped_count, "fallback": fallback_count}
        print(f"[{split}] Cropped: {cropped_count} | Fallback: {fallback_count}")

    # Write classes.txt
    classes_content = "pocket\n"
    (target_dir / "Person_1" / "classes.txt").write_text(classes_content, encoding="utf-8")

    # Create launch bats
    labelimg_exe = tools_dir / "venv" / "Scripts" / "labelImg.exe"
    
    for split in splits:
        bat_content = f"""@echo off
cd /d "%~dp0"
echo ===================================================
echo Launching LabelImg for Model B (Pockets) - {split.upper()} split
echo ===================================================
start "" "{labelimg_exe}" "%~dp0Person_1\\images\\{split}" "%~dp0Person_1\\classes.txt" "%~dp0Person_1\\labels\\{split}"
"""
        (target_dir / f"launch_{split}.bat").write_text(bat_content, encoding="utf-8")

    # Copy validate_labels.py
    validate_script_src = Path(r"C:\DEV\Projects\College_Projects\ProjectWork\ProjectWork\Annotation_Packages\validate_labels.py")
    if validate_script_src.exists():
        shutil.copy2(validate_script_src, target_dir / "validate_labels.py")

    # Create README.md for user instructions
    readme_content = """# Model B — Pocket Annotation Package

Welcome! This package contains the **cropped blister strips** automatically extracted by Model A.
Your task is to draw bounding boxes around **each individual pocket** on each blister strip.

---

## 📌 1. Rules for Pocket Annotation
- **Class Name:** `pocket` (Pre-configured in `Person_1/classes.txt`).
- **Target:** Every single pocket on the blister strip must have its own bounding box (whether filled or empty).
- **Format:** Standard **YOLO** format (`.txt` files).

---

## 🚀 2. Quick Launch
Double-click any of the launcher batch scripts:
- **`launch_train.bat`** (503 images)
- **`launch_val.bat`** (27 images)
- **`launch_test.bat`** (75 images)

This will automatically open `LabelImg` with:
- Image directory loaded
- Class set to `pocket`
- Label directory loaded

---

## ⌨️ 3. LabelImg Shortcuts
- **`W`**: Draw a new rectangle box around a pocket
- **`Ctrl + S`**: Save annotations for current image (**Always save before next image!**)
- **`D`**: Next image
- **`A`**: Previous image
- Make sure format button on the left sidebar says **`YOLO`**!

---

## ✅ 4. When Finished
Run `python validate_labels.py` to confirm all images have corresponding `.txt` label files without errors, then we can train Model B!
"""
    (target_dir / "README.md").write_text(readme_content, encoding="utf-8")

    print("\n=== Model B Annotation Package Created Successfully! ===")
    print(f"Target Directory: {target_dir}")
    print(f"Stats: {stats}")

if __name__ == "__main__":
    main()
