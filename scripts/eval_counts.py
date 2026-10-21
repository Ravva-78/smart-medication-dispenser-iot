"""
Count-accuracy harness for the vision pipeline.

Usage:
    python scripts/eval_counts.py [truth.csv] [--layout RxC|none]

truth.csv columns: file,total,present,missing[,missing_cells]
    missing_cells is optional, e.g. "r1c1;r2c1" (row/col as seen in the image, 1-based).
Image paths are resolved relative to the CSV. Exit code 1 if any image fails.
Read-only: nothing is written to disk.
"""
import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

DEFAULT_TRUTH = ROOT / "qa_testing" / "test_images" / "truth.csv"


def _cells(result):
    # getattr: older InspectionResult has no row/col; position check is then skipped.
    return sorted(f"r{p.row}c{p.col}" for p in result.pockets if p.class_name == "missing") \
        if result.pockets and hasattr(result.pockets[0], "row") else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("truth", nargs="?", default=str(DEFAULT_TRUTH))
    ap.add_argument("--layout", help="expected layout RxC (or 'none'); default = config.EXPECTED_LAYOUT")
    args = ap.parse_args()

    from app.pipeline import Pipeline
    pipe = Pipeline.from_defaults()
    if args.layout and hasattr(pipe, "expected_layout"):
        pipe.expected_layout = None if args.layout == "none" else tuple(map(int, args.layout.lower().split("x")))

    truth_path = Path(args.truth)
    rows = list(csv.DictReader(truth_path.open(newline="", encoding="utf-8")))
    failures = 0
    print(f"{'image':34} {'truth T/P/M':>12} {'got T/P/M':>12}  counts  cells  layout")
    for row in rows:
        want = (int(row["total"]), int(row["present"]), int(row["missing"]))
        r = pipe.run(truth_path.parent / row["file"])
        got = (r.total, r.present, r.missing)
        counts_ok = got == want

        want_cells = sorted(c for c in (row.get("missing_cells") or "").split(";") if c)
        got_cells = _cells(r)
        cells_ok = None if got_cells is None or "missing_cells" not in row else got_cells == want_cells

        layout_ok = getattr(r, "layout_ok", None)
        layout_txt = "n/a" if layout_ok is None else ("ok" if layout_ok else "MISMATCH")

        ok = counts_ok and cells_ok is not False
        failures += not ok
        fmt = lambda v: "n/a" if v is None else ("PASS" if v else "FAIL")
        print(f"{row['file'][:34]:34} {'/'.join(map(str, want)):>12} {'/'.join(map(str, got)):>12}  "
              f"{fmt(counts_ok):6} {fmt(cells_ok):6} {layout_txt}")
        if not ok:
            print(f"    missing cells: want {want_cells} got {got_cells}")
    print(f"\n{len(rows) - failures}/{len(rows)} passed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
