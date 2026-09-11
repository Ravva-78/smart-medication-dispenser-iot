import shutil
from pathlib import Path

def main():
    core_root = Path(r"C:\DEV\Projects\College_Projects\ProjectWork\ProjectWork\core")
    src_pkg = Path(r"C:\DEV\Projects\College_Projects\ProjectWork\ProjectWork\Annotation_Packages_Model_B\Person_1")
    dst_dataset = core_root / "models" / "model_b" / "dataset"
    backup_dataset = core_root / "models" / "model_b" / "dataset_backup_v1"

    print(f"Source Package : {src_pkg}")
    print(f"Target Dataset : {dst_dataset}")

    # 1. Backup old dataset if not already backed up
    if dst_dataset.exists() and not backup_dataset.exists():
        print(f"Creating backup of old dataset to: {backup_dataset}...")
        shutil.copytree(dst_dataset, backup_dataset)
        print("Backup created successfully.")

    # 2. Sync images and labels
    for split in ["train", "val", "test"]:
        # Images
        src_img_split = src_pkg / "images" / split
        dst_img_split = dst_dataset / "images" / split
        dst_img_split.mkdir(parents=True, exist_ok=True)

        # Clear existing images in target split
        for f in dst_img_split.glob("*.*"):
            f.unlink()

        # Copy new images
        img_files = [f for f in src_img_split.iterdir() if f.is_file()]
        for f in img_files:
            shutil.copy2(f, dst_img_split / f.name)
        print(f"Synced [{split}] images: {len(img_files)} files copied.")

        # Labels
        src_lbl_split = src_pkg / "labels" / split
        dst_lbl_split = dst_dataset / "labels" / split
        dst_lbl_split.mkdir(parents=True, exist_ok=True)

        # Clear existing labels in target split
        for f in dst_lbl_split.glob("*.txt"):
            f.unlink()

        # Copy new labels
        lbl_files = [f for f in src_lbl_split.glob("*.txt") if f.name != "classes.txt"]
        for f in lbl_files:
            shutil.copy2(f, dst_lbl_split / f.name)
        print(f"Synced [{split}] labels: {len(lbl_files)} files copied.")

    # 3. Update data.yaml
    data_yaml_path = dst_dataset / "data.yaml"
    data_yaml_content = f"""path: {dst_dataset.as_posix()}
train: images/train
val: images/val
test: images/test

names:
  0: pocket
"""
    data_yaml_path.write_text(data_yaml_content, encoding="utf-8")
    print(f"Updated {data_yaml_path} with absolute path.")

    # 4. classes.txt
    (dst_dataset / "classes.txt").write_text("pocket\n", encoding="utf-8")

    print("\nDataset synchronization complete!")

if __name__ == "__main__":
    main()
