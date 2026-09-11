import random
import shutil
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATASET_DIR = ROOT / "dataset"
VAL_SPLIT_RATIO = 0.15  # 15% validation split

random.seed(42)

def main():
    classes = ["present", "missing"]
    
    for cls in classes:
        train_cls_dir = DATASET_DIR / "train" / cls
        val_cls_dir = DATASET_DIR / "val" / cls
        val_cls_dir.mkdir(parents=True, exist_ok=True)
        
        if not train_cls_dir.exists():
            continue
            
        images = sorted([f for f in train_cls_dir.iterdir() if f.suffix.lower() in ('.jpg', '.jpeg', '.png')])
        if not images:
            continue
            
        num_val = int(len(images) * VAL_SPLIT_RATIO)
        val_samples = random.sample(images, num_val)
        
        print(f"Moving {len(val_samples)} / {len(images)} images to 'val/{cls}'...")
        for img_path in val_samples:
            dest = val_cls_dir / img_path.name
            shutil.move(str(img_path), str(dest))
            
    print("\nValidation split creation complete!")

if __name__ == "__main__":
    main()
