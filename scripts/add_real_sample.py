"""
Record a REAL household blister photo for testing, without inventing its identity.

    python scripts/add_real_sample.py path\\to\\photo.jpg --label "Dolo 650" [--source operator|packaging] [--notes "front, good light"]
    python scripts/add_real_sample.py path\\to\\photo.jpg            # unknown medicine: recorded as UNKNOWN

The image is copied (never moved or overwritten) to qa_testing/real_samples/images/ and one row is appended
to qa_testing/real_samples/samples.csv. A name is stored only when you supply it (--source operator) or
read it from the packaging (--source packaging); otherwise the label is UNKNOWN. Nothing is inferred.
"""
import argparse
import csv
import shutil
import sys
import uuid
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

DEFAULT_ROOT = Path(__file__).resolve().parent.parent / "qa_testing" / "real_samples"
SOURCES = ("operator", "packaging", "unknown")
MAX_BYTES = 15 * 1024 * 1024
FIELDS = ["sample_id", "file", "label", "label_source", "added_at", "notes"]


def add_sample(image_path, label=None, source=None, notes="", root=DEFAULT_ROOT):
    image_path, root = Path(image_path), Path(root)
    if not image_path.is_file():
        raise ValueError(f"Image not found: {image_path}")
    if image_path.stat().st_size > MAX_BYTES:
        raise ValueError("Image is larger than 15 MB.")
    if cv2.imdecode(np.fromfile(str(image_path), dtype=np.uint8), cv2.IMREAD_COLOR) is None:
        raise ValueError("File is not a decodable image.")

    label = (label or "").strip()
    if label:
        source = source or "operator"
        if source not in ("operator", "packaging"):
            raise ValueError("A named sample needs --source operator or packaging (who supplied the name?).")
    else:
        if source not in (None, "unknown"):
            raise ValueError("--source operator/packaging needs a --label.")
        label, source = "UNKNOWN", "unknown"

    sample_id = f"S-{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:4]}"
    dest = root / "images" / f"{sample_id}{image_path.suffix.lower() or '.jpg'}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        raise ValueError(f"Refusing to overwrite {dest}")
    shutil.copy2(image_path, dest)

    csv_path = root / "samples.csv"
    new_file = not csv_path.exists()
    row = {"sample_id": sample_id, "file": f"images/{dest.name}", "label": label, "label_source": source,
           "added_at": datetime.now().isoformat(timespec="seconds"), "notes": notes.strip()}
    with csv_path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerow(row)
    return row


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("--label", help="medicine name, only if you know it")
    ap.add_argument("--source", choices=SOURCES, help="who supplied the label (default: operator when --label is given)")
    ap.add_argument("--notes", default="")
    args = ap.parse_args()
    try:
        row = add_sample(args.image, args.label, args.source, args.notes)
    except ValueError as err:
        print(f"NOT ADDED: {err}")
        sys.exit(1)
    print(f"added {row['sample_id']}  label={row['label']} ({row['label_source']})  -> {row['file']}")


if __name__ == "__main__":
    main()
