import numpy as np
import cv2


def order_points(pts):
    rect = np.zeros((4, 2), dtype = "float32")

    s = pts.sum(axis = 1)
    rect[0] = pts[np.argmin(s)] # (y, x) -> (x, y)
    rect[2] = pts[np.argmax(s)]

    diff = np.diff(pts, axis = 1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]

    return rect

def persp_warp(img, pts):
    rect = order_points(pts)
    (tl, tr, br, bl) = rect

    widthA = np.hypot(br[0] - bl[0], br[1] - bl[1])
    widthB = np.hypot(tr[0] - tl[0], tr[1] - tl[1])
    maxWidth = max(int(widthA), int(widthB))

    heightA = np.hypot(tr[0] - br[0], tr[1] - br[1])
    heightB = np.hypot(tl[0] - bl[0], tl[1] - bl[1])
    maxHeight = max(int(heightA), int(heightB))

    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]], dtype = "float32")

    A = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(img, A, (maxWidth, maxHeight))
    return warped


def totori_affine_warp(img, pts, minus_one=False):
    # totori specific
    rect = order_points(pts)
    (tl, tr, br, bl) = rect
    tl = (tl - bl) * 0.1349 + tl
    rect[0] = tl
    if minus_one:
        rect -= np.array([1, 1])
    return persp_warp(img, rect)
