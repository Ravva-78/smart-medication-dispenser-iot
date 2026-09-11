import os
import shutil
from pathlib import Path

def main():
    base_pkg = Path(r"C:\DEV\Projects\College_Projects\ProjectWork\ProjectWork\Annotation_Packages_Model_B\Person_1")
    img_val_dir = base_pkg / "images" / "val"
    img_test_dir = base_pkg / "images" / "test"
    lbl_val_dir = base_pkg / "labels" / "val"
    lbl_test_dir = base_pkg / "labels" / "test"

    val_stems = {f.stem for f in img_val_dir.iterdir() if f.is_file()}
    test_stems = {f.stem for f in img_test_dir.iterdir() if f.is_file()}

    print(f"VAL target images : {len(val_stems)}")
    print(f"TEST target images: {len(test_stems)}")

    # 1. Create a backup of current labels/val just for safety
    backup_val = base_pkg / "labels" / "val_backup_before_sync"
    if not backup_val.exists():
        shutil.copytree(lbl_val_dir, backup_val)
        print(f"Created backup of old val labels at: {backup_val}")

    # 2. Identify the 27 val labels inside labels/test
    moved_count = 0
    for txt_file in list(lbl_test_dir.glob("*.txt")):
        if txt_file.name == "classes.txt":
            continue
        if txt_file.stem in val_stems:
            target_file = lbl_val_dir / txt_file.name
            shutil.move(str(txt_file), str(target_file))
            moved_count += 1

    print(f"\nMoved {moved_count} files from labels/test -> labels/val.")

    # 3. Validation check
    remaining_test_labels = [f for f in lbl_test_dir.glob("*.txt") if f.name != "classes.txt"]
    final_val_labels = [f for f in lbl_val_dir.glob("*.txt") if f.name != "classes.txt"]

    print(f"\nFinal verification:")
    print(f"  labels/test: {len(remaining_test_labels)} labels (Expected: {len(test_stems)})")
    print(f"  labels/val : {len(final_val_labels)} labels (Expected: {len(val_stems)})")

    # Check 1-to-1 match
    test_match = {f.stem for f in remaining_test_labels} == test_stems
    val_match = {f.stem for f in final_val_labels} == val_stems

    print(f"  Test 1-to-1 match: {'PERFECT' if test_match else 'MISMATCH'}")
    print(f"  Val 1-to-1 match : {'PERFECT' if val_match else 'MISMATCH'}")

    if test_match and val_match:
        print("\nAll labels are successfully separated and placed in their respective folders!")
    else:
        print("\nWarning: Some files did not match.")

if __name__ == "__main__":
    main()
