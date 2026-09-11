import json
import shutil
from datetime import date
from pathlib import Path
import torch
from ultralytics import YOLO

def main():
    core_root = Path(r"C:\DEV\Projects\College_Projects\ProjectWork\ProjectWork\core")
    model_b_dir = core_root / "models" / "model_b"
    data_yaml = model_b_dir / "dataset" / "data.yaml"
    runs_dir = model_b_dir / "runs"
    prod_dir = core_root / "models" / "production"
    prod_dir.mkdir(parents=True, exist_ok=True)

    base_model = model_b_dir / "yolo11s.pt"
    if not base_model.exists():
        base_model = core_root / "yolo11s.pt"

    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    print("=" * 60)
    print("🚀 LAUNCHING TRAINING: Model B v2.0 (Blister Pocket Detector)")
    print(f"Device: {device}")
    print(f"Base Model: {base_model}")
    print(f"Data YAML: {data_yaml}")
    print("=" * 60)

    model = YOLO(str(base_model))

    train_kwargs = dict(
        data=str(data_yaml),
        epochs=100,
        batch=8,
        imgsz=640,
        patience=30,
        workers=0,
        device=device,
        project=str(runs_dir),
        name="ModelB_v2.0",
        pretrained=True,
        optimizer="auto",
        cos_lr=True,
        amp=True,
        seed=42,
        degrees=15.0,
        mosaic=0.0,
        close_mosaic=0,
        fliplr=0.5,
        flipud=0.0,
        exist_ok=True,
        cache=True,
        save=True,
        val=True,
        plots=True,
    )

    results = model.train(**train_kwargs)
    save_dir = Path(getattr(results, "save_dir", None) or (runs_dir / "ModelB_v2.0"))
    best_weights = save_dir / "weights" / "best.pt"

    print("\n" + "=" * 60)
    print("✅ Training complete!")
    print(f"Best weights saved at: {best_weights}")
    print("=" * 60)

    # 1. Copy to production
    prod_weights = prod_dir / "ModelB_v2.0.pt"
    if best_weights.exists():
        shutil.copy2(best_weights, prod_weights)
        print(f"Exported to production: {prod_weights}")

    # 2. Evaluate on holdout test set
    print("\nEvaluating Model B v2.0 on holdout test split...")
    eval_model = YOLO(str(prod_weights))
    val_metrics = eval_model.val(data=str(data_yaml), split="val", imgsz=640, batch=8, device=device)
    test_metrics = eval_model.val(data=str(data_yaml), split="test", imgsz=640, batch=8, device=device)

    p_val = float(val_metrics.results_dict.get("metrics/precision(B)", 0.0))
    r_val = float(val_metrics.results_dict.get("metrics/recall(B)", 0.0))
    map50_val = float(val_metrics.results_dict.get("metrics/mAP50(B)", 0.0))
    map50_95_val = float(val_metrics.results_dict.get("metrics/mAP50-95(B)", 0.0))

    p_test = float(test_metrics.results_dict.get("metrics/precision(B)", 0.0))
    r_test = float(test_metrics.results_dict.get("metrics/recall(B)", 0.0))
    map50_test = float(test_metrics.results_dict.get("metrics/mAP50(B)", 0.0))
    map50_95_test = float(test_metrics.results_dict.get("metrics/mAP50-95(B)", 0.0))

    # 3. Create ModelB_v2.0.json
    meta = {
        "name": "Blister Pocket Detector",
        "version": "2.0.0",
        "stage": 3,
        "architecture": "YOLO11s",
        "imgsz": 640,
        "confidence_threshold": 0.50,
        "precision": round(p_val, 4),
        "recall": round(r_val, 4),
        "mAP50": round(map50_val, 4),
        "mAP50_95": round(map50_95_val, 4),
        "test_precision": round(p_test, 4),
        "test_recall": round(r_test, 4),
        "test_mAP50": round(map50_test, 4),
        "test_mAP50_95": round(map50_95_test, 4),
        "training_dataset": "Blister Pocket Dataset v2 (Person_1)",
        "total_images": 605,
        "train_images": 503,
        "val_images": 27,
        "test_images": 75,
        "device": f"{device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})",
        "date": str(date.today())
    }

    prod_json = prod_dir / "ModelB_v2.0.json"
    prod_json.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Generated production metadata: {prod_json}")

    print("\n" + "=" * 60)
    print("🎉 MODEL B v2.0 READY FOR PRODUCTION!")
    print(f"Validation mAP@50 : {map50_val*100:.2f}% (Recall: {r_val*100:.2f}%)")
    print(f"Test Holdout mAP@50: {map50_test*100:.2f}% (Recall: {r_test*100:.2f}%)")
    print(f"Weights: {prod_weights}")
    print(f"Report : {prod_json}")
    print("=" * 60)

if __name__ == "__main__":
    main()
