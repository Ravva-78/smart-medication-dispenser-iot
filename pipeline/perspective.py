"""
Perspective correction for blister strip images.

Detects the four corners of the strip and applies a warp
perspective transform to produce a front-on rectified view.
"""
import cv2
import numpy as np


def correct_perspective(image, output_width=800, output_height=600):
    """
    Detect strip quadrilateral and warp to front-on view.
    
    Args:
        image: BGR numpy array
        output_width, output_height: dimensions of the rectified output
    
    Returns:
        rectified image, or original if corners can't be found
    """
    orig = image.copy()
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 50, 200)

    contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return orig

    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    h, w = image.shape[:2]
    img_area = h * w

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 0.25 * img_area:
            continue

        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)

        if len(approx) == 4:
            corners = approx.reshape(4, 2).astype(np.float32)
            rect = _order_corners(corners)
            w_box = np.linalg.norm(rect[1] - rect[0])
            h_box = np.linalg.norm(rect[3] - rect[0])
            if h_box > w_box and output_width > output_height:
                ow, oh = output_height, output_width
            else:
                ow, oh = output_width, output_height
            dst = np.array([
                [0, 0],
                [ow - 1, 0],
                [ow - 1, oh - 1],
                [0, oh - 1],
            ], dtype=np.float32)
            matrix = cv2.getPerspectiveTransform(rect, dst)
            rectified = cv2.warpPerspective(orig, matrix, (ow, oh))
            return rectified



    return orig


def _order_corners(pts):
    """Order corners: top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect
