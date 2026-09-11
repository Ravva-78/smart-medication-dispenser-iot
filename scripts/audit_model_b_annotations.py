import os
from pathlib import Path

def audit():
    base_pkg = Path(r"C:\DEV\Projects\College_Projects\ProjectWork\ProjectWork\Annotation_Packages_Model_B")
    print(f"Checking package directory: {base_pkg}")
    if not base_pkg.exists():
        print(f"ERROR: Directory {base_pkg} does not exist!")
        return

    # Look for image and label directories
    # Typical structure: Person_1/images and Person_1/labels or direct images/labels
    person_dir = base_pkg / "Person_1"
    if not person_dir.exists():
        print("Looking at top-level folders since Person_1 was not directly found...")
        person_dir = base_pkg

    img_dir = person_dir / "images"
    lbl_dir = person_dir / "labels"

    print(f"\n--- Exploring Structure under {person_dir} ---")
    if img_dir.exists():
        print("Images directory exists:")
        for p in img_dir.iterdir():
            if p.is_dir():
                count = len([f for f in p.iterdir() if f.is_file() and not f.name.endswith('.txt')])
                print(f"  [images/{p.name}]: {count} files")
    else:
        print("Images directory NOT found under person_dir!")

    if lbl_dir.exists():
        print("\nLabels directory exists:")
        for p in lbl_dir.iterdir():
            if p.is_dir():
                count = len([f for f in p.iterdir() if f.is_file()])
                print(f"  [labels/{p.name}]: {count} files")
    else:
        print("Labels directory NOT found under person_dir!")

    # Check for any other folders in base_pkg
    print("\nAll items directly in Annotation_Packages_Model_B:")
    for item in base_pkg.iterdir():
        print(f"  - {item.name} ({'DIR' if item.is_dir() else 'FILE'})")

    # Image stems for each split
    splits = ["train", "val", "test"]
    split_images = {}
    for s in splits:
        s_dir = img_dir / s if img_dir.exists() else None
        if s_dir and s_dir.exists():
            stems = {f.stem: f for f in s_dir.iterdir() if f.is_file()}
            split_images[s] = stems
        else:
            split_images[s] = {}

    print(f"\nImage counts detected:")
    for s, imgs in split_images.items():
        print(f"  {s}: {len(imgs)} images")

    # Search for all .txt files in labels directory and subdirectories
    all_label_files = []
    if lbl_dir.exists():
        for root, dirs, files in os.walk(lbl_dir):
            for file in files:
                if file.endswith(".txt") and file != "classes.txt":
                    all_label_files.append(Path(root) / file)

    print(f"\nFound {len(all_label_files)} label .txt files across all label subfolders.")

    # Check where these label files currently reside
    lbl_locations = {}
    for f in all_label_files:
        rel = f.relative_to(lbl_dir).parent
        lbl_locations[str(rel)] = lbl_locations.get(str(rel), 0) + 1
    print(f"Label file distribution by folder: {lbl_locations}")

    # Map labels to images
    val_matched = []
    test_matched = []
    train_matched = []
    unmatched = []

    label_details = {} # stem: {'split': ..., 'boxes': ..., 'path': ...}

    for lbl in all_label_files:
        stem = lbl.stem
        # Read content
        try:
            lines = [l.strip() for l in lbl.read_text(encoding="utf-8").splitlines() if l.strip()]
        except Exception:
            lines = [l.strip() for l in lbl.read_text(encoding="latin-1").splitlines() if l.strip()]
        
        num_boxes = len(lines)
        
        if stem in split_images["val"]:
            val_matched.append((lbl, num_boxes))
            label_details[stem] = {"target_split": "val", "boxes": num_boxes, "current_path": str(lbl)}
        elif stem in split_images["test"]:
            test_matched.append((lbl, num_boxes))
            label_details[stem] = {"target_split": "test", "boxes": num_boxes, "current_path": str(lbl)}
        elif stem in split_images["train"]:
            train_matched.append((lbl, num_boxes))
            label_details[stem] = {"target_split": "train", "boxes": num_boxes, "current_path": str(lbl)}
        else:
            unmatched.append((lbl, num_boxes))

    print("\n================= MAPPING RESULTS =================")
    print(f"Total Labels Found: {len(all_label_files)}")
    print(f"Mapped to VAL  (Target: {len(split_images['val'])} images) : {len(val_matched)} labels found")
    print(f"Mapped to TEST (Target: {len(split_images['test'])} images): {len(test_matched)} labels found")
    print(f"Mapped to TRAIN (Target: {len(split_images['train'])} images): {len(train_matched)} labels found")
    print(f"Unmatched labels: {len(unmatched)}")

    # Check for missing annotations in val and test
    val_missing = [stem for stem in split_images["val"] if stem not in label_details]
    test_missing = [stem for stem in split_images["test"] if stem not in label_details]

    print("\n--- Missing Annotations Status ---")
    if val_missing:
        print(f"VAL missing {len(val_missing)} annotations: {val_missing}")
    else:
        print("VAL: ALL images have matching annotations! (100% annotated)")

    if test_missing:
        print(f"TEST missing {len(test_missing)} annotations: {test_missing}")
    else:
        print("TEST: ALL images have matching annotations! (100% annotated)")

    # Box counts summary
    print("\n--- Box Count Inspection ---")
    val_empty = [lbl.name for lbl, b in val_matched if b == 0]
    test_empty = [lbl.name for lbl, b in test_matched if b == 0]
    
    val_boxes = [b for _, b in val_matched]
    test_boxes = [b for _, b in test_matched]

    if val_boxes:
        print(f"VAL: Total boxes = {sum(val_boxes)}, Min boxes/img = {min(val_boxes)}, Max = {max(val_boxes)}, Avg = {sum(val_boxes)/len(val_boxes):.1f}")
    if val_empty:
        print(f"  WARNING: VAL has {len(val_empty)} empty label files (0 boxes): {val_empty}")

    if test_boxes:
        print(f"TEST: Total boxes = {sum(test_boxes)}, Min boxes/img = {min(test_boxes)}, Max = {max(test_boxes)}, Avg = {sum(test_boxes)/len(test_boxes):.1f}")
    if test_empty:
        print(f"  WARNING: TEST has {len(test_empty)} empty label files (0 boxes): {test_empty}")

    if unmatched:
        print(f"\nUnmatched files detail: {[u[0].name for u in unmatched]}")

if __name__ == "__main__":
    audit()
