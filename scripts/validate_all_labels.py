from pathlib import Path

base_pkg = Path(r"C:\DEV\Projects\College_Projects\ProjectWork\ProjectWork\Annotation_Packages_Model_B\Person_1")
test_lbl_dir = base_pkg / "labels" / "test"
img_val_dir = base_pkg / "images" / "val"
img_test_dir = base_pkg / "images" / "test"

val_stems = {f.stem for f in img_val_dir.iterdir() if f.is_file()}
test_stems = {f.stem for f in img_test_dir.iterdir() if f.is_file()}

print("Validating labels in labels/test (where all 102 are located)...")
errors = []
total_boxes = 0
val_boxes_count = 0
test_boxes_count = 0

for txt_file in test_lbl_dir.glob("*.txt"):
    if txt_file.name == "classes.txt":
        continue
    stem = txt_file.stem
    is_val = stem in val_stems
    is_test = stem in test_stems
    
    if not is_val and not is_test:
        errors.append(f"Unknown file: {txt_file.name}")
        continue
        
    lines = [l.strip() for l in txt_file.read_text(encoding='utf-8', errors='ignore').splitlines() if l.strip()]
    if len(lines) == 0:
        errors.append(f"Empty annotation file: {txt_file.name}")
        continue
        
    for idx, line in enumerate(lines):
        parts = line.split()
        if len(parts) != 5:
            errors.append(f"{txt_file.name} line {idx+1}: invalid format '{line}'")
            continue
        try:
            cls = int(parts[0])
            x, y, w, h = map(float, parts[1:])
            if cls != 0:
                errors.append(f"{txt_file.name} line {idx+1}: unexpected class id {cls}")
            if not (0 <= x <= 1 and 0 <= y <= 1 and 0 < w <= 1 and 0 < h <= 1):
                errors.append(f"{txt_file.name} line {idx+1}: bbox out of bounds {parts}")
        except ValueError as e:
            errors.append(f"{txt_file.name} line {idx+1}: parse error {e}")
            
    total_boxes += len(lines)
    if is_val:
        val_boxes_count += len(lines)
    if is_test:
        test_boxes_count += len(lines)

print(f"Validation finished.")
print(f"Total Errors Found: {len(errors)}")
if errors:
    for err in errors[:10]:
        print(f"  - {err}")
    if len(errors) > 10:
        print(f"  ... and {len(errors)-10} more")
else:
    print("ALL 102 label files are 100% valid YOLO format! Zero errors.")
    print(f"Total pockets (bounding boxes) in test set (75 images): {test_boxes_count} boxes (avg {test_boxes_count/75:.1f} per strip)")
    print(f"Total pockets (bounding boxes) in val set (27 images) : {val_boxes_count} boxes (avg {val_boxes_count/27:.1f} per strip)")
