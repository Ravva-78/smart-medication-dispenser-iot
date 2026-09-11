"""
Blind Dataset Evaluation & Hold-out Benchmark Script.

Purpose:
    Evaluates the complete end-to-end vision pipeline (Model A -> Perspective -> Model B -> Model C -> InventoryState)
    on unseen test image folders in TABLET_DATA.

Folders & Ground Truth Mapping:
    - FULL_STRIP                  -> GT Missing = 0
    - ONE_SLOT_EMPTY_STRIP        -> GT Missing = 1
    - TWO_&THREE_SLOT_EMPTY_STRIP  -> GT Missing = 2
    - FOUR_SLOT_EMPTY_STRIP       -> GT Missing = 4
    - SEVEN_SLOT_EMPTY_STRIP      -> GT Missing = 7

Outputs:
    - evaluation_results/report.csv
    - evaluation_results/summary.json
    - evaluation_results/passed/ (copies of successful evaluations)
    - evaluation_results/failed/ (copies of failed evaluations for root cause inspection)
"""

import sys
import json
import time
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timezone
import cv2
import pandas as pd

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.pipeline import Pipeline

logger = logging.getLogger(__name__)

# Ground Truth Mapping by Folder Name
GT_MAPPING = {
    "FULL_STRIP": 0,
    "ONE_SLOT_EMPTY_STRIP": 1,
    "TWO_&THREE_SLOT_EMPTY_STRIP": 2,
    "FOUR_SLOT_EMPTY_STRIP": 4,
    "SEVEN_SLOT_EMPTY_STRIP": 7,
}


def run_blind_evaluation(
    dataset_dir: Path,
    output_dir: Path,
    max_per_folder: int = 50,
) -> Dict[str, Any]:
    """
    Run complete evaluation on unseen dataset directory.

    Args:
        dataset_dir: Path to TABLET_DATA directory.
        output_dir: Path to save evaluation_results/.
        max_per_folder: Maximum images to evaluate per category folder.

    Returns:
        Summary metrics dictionary.
    """
    print(f"=== Starting Blind Dataset Evaluation ===")
    print(f"Dataset Path: {dataset_dir}")
    print(f"Output Path:  {output_dir}")

    # Prepare output directories
    passed_dir = output_dir / "passed"
    failed_dir = output_dir / "failed"
    passed_dir.mkdir(parents=True, exist_ok=True)
    failed_dir.mkdir(parents=True, exist_ok=True)

    # Initialize Vision Pipeline
    pipeline = Pipeline.from_defaults()

    results: List[Dict[str, Any]] = []
    category_metrics: Dict[str, Any] = {}

    for folder_name, gt_missing in GT_MAPPING.items():
        folder_path = dataset_dir / folder_name
        if not folder_path.exists():
            print(f"⚠️ Warning: Folder {folder_name} not found at {folder_path}")
            continue

        image_files = list(folder_path.glob("*.jpg")) + list(folder_path.glob("*.png")) + list(folder_path.glob("*.jpeg"))
        if max_per_folder > 0:
            image_files = image_files[:max_per_folder]

        print(f"\n📂 Evaluating Category: {folder_name} ({len(image_files)} images, GT Missing={gt_missing})")

        cat_passed = 0
        cat_total = len(image_files)

        for idx, img_path in enumerate(image_files, 1):
            t_start = time.perf_counter()
            img_bgr = cv2.imread(str(img_path))
            if img_bgr is None:
                print(f"  [{idx}/{cat_total}] ❌ Could not load {img_path.name}")
                continue

            # Run Vision Pipeline
            try:
                insp_res = pipeline.run(img_bgr)
                pred_missing = insp_res.missing
                total_slots = insp_res.total
                avg_conf = insp_res.avg_confidence
            except Exception as err:
                print(f"  [{idx}/{cat_total}] ❌ Pipeline error on {img_path.name}: {err}")
                pred_missing = -1
                total_slots = 0
                avg_conf = 0.0

            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            is_correct = (pred_missing == gt_missing)

            if is_correct:
                cat_passed += 1
                dest_file = passed_dir / f"{folder_name}_{img_path.name}"
            else:
                dest_file = failed_dir / f"{folder_name}_{img_path.name}"

            # Copy image to passed/failed destination
            try:
                shutil.copy(img_path, dest_file)
            except Exception:
                pass

            status_str = "PASS [OK]" if is_correct else f"FAIL [GT={gt_missing}, Pred={pred_missing}]"
            print(f"  [{idx}/{cat_total}] {img_path.name[:30]:<30} | GT: {gt_missing} | Pred: {pred_missing} | {status_str} | ({elapsed_ms:.0f}ms)")

            results.append({
                "Image": img_path.name,
                "Folder": folder_name,
                "GT_Missing": gt_missing,
                "Predicted_Missing": pred_missing,
                "Total_Slots": total_slots,
                "Correct": "YES" if is_correct else "NO",
                "Confidence": round(avg_conf, 4),
                "Latency_ms": round(elapsed_ms, 2),
            })

        acc_pct = (cat_passed / cat_total * 100.0) if cat_total > 0 else 0.0
        category_metrics[folder_name] = {
            "gt_missing": gt_missing,
            "total_images": cat_total,
            "passed": cat_passed,
            "failed": cat_total - cat_passed,
            "accuracy_pct": round(acc_pct, 2),
        }
        print(f"  ──► Category Accuracy [{folder_name}]: {acc_pct:.1f}% ({cat_passed}/{cat_total})")

    # Export CSV Report
    df_report = pd.DataFrame(results)
    csv_path = output_dir / "report.csv"
    df_report.to_csv(csv_path, index=False)

    # Compute Overall Summary
    total_eval = len(results)
    total_pass = sum(1 for r in results if r["Correct"] == "YES")
    overall_acc = (total_pass / total_eval * 100.0) if total_eval > 0 else 0.0
    avg_total_ms = sum(float(r["Latency_ms"]) for r in results) / total_eval if total_eval > 0 else 0.0

    summary = {
        "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
        "total_images_evaluated": total_eval,
        "total_passed": total_pass,
        "total_failed": total_eval - total_pass,
        "overall_accuracy_pct": round(overall_acc, 2),
        "average_latency_ms": round(avg_total_ms, 2),
        "category_metrics": category_metrics,
        "report_csv_path": str(csv_path),
        "failed_images_dir": str(failed_dir),
    }

    # Save summary.json
    json_path = output_dir / "summary.json"
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2)

    print("\n==========================================")
    print(f" BLIND DATASET EVALUATION COMPLETE")
    print(f" Overall Accuracy: {overall_acc:.2f}% ({total_pass}/{total_eval})")
    print(f" Report Saved:     {csv_path}")
    print(f" Failed Images:    {failed_dir}")
    print("==========================================")

    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    dataset_path = Path(r"C:\Users\nan33\OneDrive\Desktop\summer_projects\TABLET_DATA")
    output_path = ROOT / "evaluation_results"
    run_blind_evaluation(dataset_path, output_path, max_per_folder=20)
