# Model B — Pocket Annotation Guide

Welcome! This folder contains the cropped blister strip dataset for **Model B (Pocket Detector)**. Your task is to annotate the individual blister pockets in these images.

---

## 📌 1. Goal & Pre-defined Class

*   **Task:** Draw bounding boxes around **every individual pocket** on each blister strip.
*   **Class Name:** Exactly **`pocket`** (Single class).
*   **Target:** Every pocket (whether filled with a pill or empty) must have its own bounding box.

```text
Visual Example:
[  O   O   O   O  ]  <-- Blister Strip Image
  └─── └─── └─── └───
   □    □    □    □   <-- One bounding box labeled 'pocket' per item
```

---

## 🚀 2. How to Launch LabelImg


### Method: Via Python Terminal
```bash
pip install labelImg pyqt5   or  `pip install labelImg`  
labelImg
``` 


## 📂 3. Opening Directories in LabelImg

When `labelImg` opens, set your directories for the split you are currently annotating (e.g. `train`):

1. **Set Image Input Directory:**
   * Click **Open Dir** on the left toolbar.
   * Select: `Model_B/dataset/images/train/` (or `val/`, `test/`).

2. **Set Label Output Save Directory:**
   * Click **Change Save Dir** on the left toolbar.
   * Select: `Model_B/dataset/labels/train/` (or `val/`, `test/`).
   * *Note: `labelImg` will save matching `.txt` annotation files directly into this directory.*

3. **Toggle Output Format (CRITICAL):**
   * Locate the format toggle button on the left sidebar (which defaults to **PascalVOC**).
   * **Click it until it displays `YOLO`**.
   * ⚠️ *If you do not change it to YOLO, the tool will save `.xml` files instead of `.txt` files, which cannot be used for training!*

---

## ✏️ 4. Drawing Rules

1.  Press **`W`** on your keyboard to activate the rectangle drawing cursor.
2.  Draw a tight bounding box around **one single pocket**.
3.  Select or type **`pocket`** as the class label.
4.  Repeat for **every pocket** on that blister strip.
5.  Press **`Ctrl + S`** to **Save** your annotations for the current image.
6.  Press **`D`** to navigate to the **Next Image**.

---

## ⌨️ 5. Keyboard Shortcuts Quick Reference

| Key Combo | Action |
| :--- | :--- |
| **`W`** | Start drawing a new bounding box |
| **`Ctrl + S`** | **Save annotations for current image (MUST DO BEFORE NEXT IMAGE)** |
| **`D`** | Go to Next Image |
| **`A`** | Go to Previous Image |
| **`Space`** | Mark current image as verified |
| **`Del`** | Delete selected bounding box |

---

## ⚠️ 6. Common Mistakes to Avoid

*   ❌ **Forgetting to Save:** Always press `Ctrl + S` before pressing `D`.
*   ❌ **Drawing one box around the whole strip:** Draw **separate boxes** for each pocket.
*   ❌ **Using PascalVOC format:** Format button MUST say **YOLO**.
*   ❌ **Creating new class names:** Only use `pocket`.
*   ❌ **Mismatched Directories:** Always match `images/train/` with `labels/train/`, `images/val/` with `labels/val/`, and `images/test/` with `labels/test/`.

---

## ✅ 7. Completion Checklist

When you finish annotating a split (e.g. `train`):
1. Open `Model_B/dataset/labels/train/`.
2. Ensure there is a `.txt` file for every image in `Model_B/dataset/images/train/`.
3. Inform the project owner so Model B training can begin!
