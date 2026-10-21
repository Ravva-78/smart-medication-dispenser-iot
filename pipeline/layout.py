"""
Pocket grid ordering and expected-layout check.

Model B returns boxes in confidence order, so pocket indices carry no position.
`order_boxes` clusters box centres into rows/columns and returns reading order
(row-major, as seen in the image) plus each box's 1-based (row, col).
"""
import numpy as np


def _cluster(values, tol):
    """Cluster 1-D values; a gap > tol starts a new cluster. Returns cluster id per value."""
    order = np.argsort(values)
    ids = np.zeros(len(values), dtype=int)
    cid = 0
    for k in range(1, len(order)):
        if values[order[k]] - values[order[k - 1]] > tol:
            cid += 1
        ids[order[k]] = cid
    return ids


def order_boxes(boxes):
    """
    Args:
        boxes: sequence of (x1, y1, x2, y2).
    Returns:
        (order, cells, rows, cols): `order` indexes `boxes` in row-major order,
        `cells` is [(row, col)] aligned with `order`.
    """
    b = np.asarray(boxes, dtype=float).reshape(-1, 4)
    if len(b) == 0:
        return [], [], 0, 0
    cx, cy = (b[:, 0] + b[:, 2]) / 2, (b[:, 1] + b[:, 3]) / 2
    # shortcut: half a median box size as tolerance; fine for evenly spaced blisters, revisit for skewed strips.
    row_id = _cluster(cy, 0.5 * np.median(b[:, 3] - b[:, 1]))
    col_id = _cluster(cx, 0.5 * np.median(b[:, 2] - b[:, 0]))
    order = sorted(range(len(b)), key=lambda i: (row_id[i], cx[i]))
    cells = [(int(row_id[i]) + 1, int(col_id[i]) + 1) for i in order]
    return order, cells, int(row_id.max()) + 1, int(col_id.max()) + 1


def check_layout(total, rows, cols, expected):
    """
    Compare a detected grid to the expected (rows, cols); orientation-agnostic
    (a 2x5 strip photographed sideways is 5x2). Returns (ok, message).
    """
    if expected is None:
        return True, ""
    exp_total = expected[0] * expected[1]
    regular = total == rows * cols
    if regular and sorted((rows, cols)) == sorted(expected):
        return True, ""
    return False, (f"expected {expected[0]}x{expected[1]} ({exp_total} pockets), "
                   f"found {rows}x{cols} grid with {total} pockets"
                   + ("" if regular else " (irregular grid)"))
