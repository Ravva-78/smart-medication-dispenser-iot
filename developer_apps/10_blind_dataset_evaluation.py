"""
Developer App 10: Hold-Out Blind Dataset Evaluator & Benchmark Dashboard.

Purpose:
    Provides an interactive benchmark station to run the complete end-to-end vision pipeline
    on completely unseen hold-out test dataset folders (TABLET_DATA).

Features:
    - Dataset Path & Category Selection
    - Real-Time Progress Bar & Processing Telemetry
    - Overall Accuracy & Category-Level Accuracy Tables
    - Failed Images Root Cause Gallery
    - Download CSV Benchmark Report Button
"""

import sys
import json
import time
import shutil
from pathlib import Path
from datetime import datetime, timezone
import cv2
import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.pipeline import Pipeline
from scripts.evaluate_unseen_dataset import GT_MAPPING, run_blind_evaluation

st.set_page_config(page_title="10 - Blind Dataset Evaluator", page_icon="🧪", layout="wide")
st.title("🧪 10. Unseen Hold-Out Dataset Benchmark Evaluator")
st.caption("Official Model Generalization Benchmark across Unseen Blister-Strip Folders (TABLET_DATA)")

# ─── Sidebar Configuration ──────────────────────────────────────────────────────
st.sidebar.header("⚙️ Evaluation Parameters")

default_data_dir = r"C:\Users\nan33\OneDrive\Desktop\summer_projects\TABLET_DATA"
dataset_dir_str = st.sidebar.text_input("Dataset Directory Path", value=default_data_dir)
dataset_dir = Path(dataset_dir_str)

max_images_per_folder = st.sidebar.number_input("Max Images Per Category", min_value=1, max_value=200, value=15)
output_dir = ROOT / "evaluation_results"

# ─── Top Level Controls ─────────────────────────────────────────────────────────
st.markdown("### 📂 Hold-Out Dataset Folders & Ground Truth Mapping")

gt_col1, gt_col2, gt_col3, gt_col4, gt_col5 = st.columns(5)
gt_col1.metric("FULL_STRIP", "0 Missing")
gt_col2.metric("ONE_SLOT_EMPTY", "1 Missing")
gt_col3.metric("TWO_&THREE_SLOT", "2 Missing")
gt_col4.metric("FOUR_SLOT_EMPTY", "4 Missing")
gt_col5.metric("SEVEN_SLOT_EMPTY", "7 Missing")

st.markdown("---")

run_eval_btn = st.button("🚀 Run Blind Dataset Benchmark Evaluation", type="primary", use_container_width=True)

if run_eval_btn:
    if not dataset_dir.exists():
        st.error(f"❌ Dataset directory '{dataset_dir}' does not exist!")
        st.stop()

    passed_dir = output_dir / "passed"
    failed_dir = output_dir / "failed"
    passed_dir.mkdir(parents=True, exist_ok=True)
    failed_dir.mkdir(parents=True, exist_ok=True)

    pipeline = Pipeline.from_defaults()

    results = []
    progress_bar = st.progress(0.0)
    status_text = st.empty()
    live_img_placeholder = st.empty()

    # Collect all image files
    all_tasks = []
    for folder_name, gt_missing in GT_MAPPING.items():
        folder_path = dataset_dir / folder_name
        if folder_path.exists():
            files = list(folder_path.glob("*.jpg")) + list(folder_path.glob("*.png")) + list(folder_path.glob("*.jpeg"))
            files = files[:max_images_per_folder]
            for f in files:
                all_tasks.append((folder_name, gt_missing, f))

    total_tasks = len(all_tasks)
    if total_tasks == 0:
        st.warning("No test images found in specified dataset directory!")
        st.stop()

    t_start_all = time.perf_counter()

    for idx, (folder_name, gt_missing, img_path) in enumerate(all_tasks, 1):
        status_text.markdown(f"**Processing ({idx}/{total_tasks})**: `{folder_name}/{img_path.name}`")
        progress_bar.progress(float(idx / total_tasks))

        t_start = time.perf_counter()
        img_bgr = cv2.imread(str(img_path))
        if img_bgr is None:
            continue

        try:
            insp_res = pipeline.run(img_bgr)
            pred_missing = insp_res.missing
            total_slots = insp_res.total
            avg_conf = insp_res.avg_confidence
        except Exception:
            pred_missing = -1
            total_slots = 0
            avg_conf = 0.0

        elapsed_ms = (time.perf_counter() - t_start) * 1000.0
        is_correct = (pred_missing == gt_missing)

        dest_dir = passed_dir if is_correct else failed_dir
        try:
            shutil.copy(img_path, dest_dir / f"{folder_name}_{img_path.name}")
        except Exception:
            pass

        results.append({
            "Image": img_path.name,
            "Category Folder": folder_name,
            "GT Missing": gt_missing,
            "Predicted Missing": pred_missing,
            "Total Slots": total_slots,
            "Correct": "YES" if is_correct else "NO",
            "Confidence": round(avg_conf, 4),
            "Latency (ms)": round(elapsed_ms, 1),
        })

    t_total_sec = time.perf_counter() - t_start_all
    progress_bar.progress(1.0)
    status_text.success(f"🎉 Evaluation Complete! Processed {total_tasks} hold-out images in {t_total_sec:.1f} seconds.")

    # Store results in session state
    df_res = pd.DataFrame(results)
    st.session_state["eval_df"] = df_res
    st.session_state["eval_total_sec"] = t_total_sec

# ─── Results & Report Dashboard ─────────────────────────────────────────────────
if "eval_df" in st.session_state:
    df_res = st.session_state["eval_df"]
    t_tot_sec = st.session_state["eval_total_sec"]

    st.markdown("---")
    st.subheader("📊 Benchmark Results & Performance Summary")

    total_eval = len(df_res)
    total_pass = sum(1 for c in df_res["Correct"] if c == "YES")
    total_fail = total_eval - total_pass
    overall_acc = (total_pass / total_eval * 100.0) if total_eval > 0 else 0.0
    avg_lat = df_res["Latency (ms)"].mean() if total_eval > 0 else 0.0

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Evaluated Images", total_eval)
    k2.metric("Passed (Correct)", total_pass)
    k3.metric("Failed (Mismatch)", total_fail, delta=f"{total_fail} Failed" if total_fail > 0 else "0 Failed", delta_color="inverse")
    k4.metric("Overall Accuracy", f"{overall_acc:.1f}%")
    k5.metric("Avg Latency", f"{avg_lat:.0f} ms")

    # Category Accuracy Table
    st.markdown("### Accuracy Breakdown by Category Folder")
    cat_summary = []
    for cat, group in df_res.groupby("Category Folder"):
        c_pass = sum(1 for c in group["Correct"] if c == "YES")
        c_tot = len(group)
        c_acc = (c_pass / c_tot * 100.0) if c_tot > 0 else 0.0
        cat_summary.append({
            "Category Folder": cat,
            "GT Missing": group["GT Missing"].iloc[0],
            "Total Images": c_tot,
            "Passed": c_pass,
            "Failed": c_tot - c_pass,
            "Accuracy": f"{c_acc:.1f}%",
        })
    st.dataframe(pd.DataFrame(cat_summary), use_container_width=True)

    # Detailed Table
    st.markdown("### Per-Image Evaluation Log Table")
    st.dataframe(df_res, use_container_width=True)

    # CSV Download Button
    csv_bytes = df_res.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download CSV Evaluation Report (report.csv)",
        data=csv_bytes,
        file_name="evaluation_report.csv",
        mime="text/csv",
    )

    # Failed Cases Gallery
    st.markdown("---")
    st.subheader("🚨 Root Cause Gallery — Failed Evaluations")
    failed_rows = df_res[df_res["Correct"] == "NO"]

    if not failed_rows.empty:
        st.warning(f"Found {len(failed_rows)} failed evaluation(s). Inspecting root cause below:")
        failed_dir = output_dir / "failed"
        f_cols = st.columns(min(4, len(failed_rows)))
        for idx, (_, row) in enumerate(failed_rows.iterrows()):
            f_img_path = failed_dir / f"{row['Category Folder']}_{row['Image']}"
            with f_cols[idx % len(f_cols)]:
                if f_img_path.exists():
                    st.image(str(f_img_path), caption=f"GT: {row['GT Missing']} | Pred: {row['Predicted Missing']}", use_container_width=True)
                else:
                    st.caption(f"{row['Image']} (GT={row['GT Missing']}, Pred={row['Predicted Missing']})")
    else:
        st.success("🎉 Perfect Benchmark Score! Zero failed evaluations.")
