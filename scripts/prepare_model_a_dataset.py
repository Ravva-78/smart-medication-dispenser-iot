import shutil
from pathlib import Path

def main():
    core_root = Path(__file__).resolve().parent.parent
    dataset_root = core_root / "dataset"
    source_root = Path(r"C:\DEV\Projects\College_Projects\ProjectWork\ProjectWork\Annotation_Packages\Person_1")

    splits = ["train", "val", "test"]

    print("Populating core/dataset with real annotated images from Person_1...")
    
    for split in splits:
        src_img_dir = source_root / "images" / split
        src_lbl_dir = source_root / "labels" / split

        dst_img_dir = dataset_root / "images" / split
        dst_lbl_dir = dataset_root / "labels" / split

        # Recreate destination directories
        if dst_img_dir.exists():
            shutil.rmtree(dst_img_dir)
        if dst_lbl_dir.exists():
            shutil.rmtree(dst_lbl_dir)

        dst_img_dir.mkdir(parents=True, exist_ok=True)
        dst_lbl_dir.mkdir(parents=True, exist_ok=True)

        # Copy images
        img_count = 0
        for img_file in src_img_dir.iterdir():
            if img_file.is_file() and img_file.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
                shutil.copy2(img_file, dst_img_dir / img_file.name)
                img_count += 1

        # Copy labels (exclude classes.txt)
        lbl_count = 0
        for lbl_file in src_lbl_dir.iterdir():
            if lbl_file.is_file() and lbl_file.suffix.lower() == ".txt" and lbl_file.name != "classes.txt":
                shutil.copy2(lbl_file, dst_lbl_dir / lbl_file.name)
                lbl_count += 1

        print(f"Split [{split}]: copied {img_count} images and {lbl_count} labels")

    # Verify / write data.yaml
    data_yaml_path = dataset_root / "data.yaml"
    yaml_content = f"""path: {dataset_root.as_posix()}
train: images/train
val: images/val
test: images/test

names:
  0: blister_strip
"""
    data_yaml_path.write_text(yaml_content, encoding="utf-8")

    # Also sync root data.yaml
    (core_root / "data.yaml").write_text(yaml_content, encoding="utf-8")
    (core_root / "models" / "model_a" / "data.yaml").write_text(yaml_content, encoding="utf-8")

    print("\nDataset preparation completed successfully!")

if __name__ == "__main__":
    main()
