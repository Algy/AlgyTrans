#!/usr/bin/env python

import sys
import numpy as np
import cv2

from persp import persp_warp

if __name__ == '__main__':
    src = sys.argv[1]
    img = cv2.imread(src)

    flooded = img.copy()
    hsv = cv2.cvtColor(img,cv2.COLOR_BGR2HSV)

    cannied = cv2.Canny(img, 40, 80)
    cannied = cv2.GaussianBlur(cannied, (15, 15), 0)

    mask = cv2.copyMakeBorder(cannied, 1, 1, 1, 1, cv2.BORDER_REPLICATE)

    # img[cannied != 0] = [255, 255, 255]
    # hsv[cannied != 0] = [255, 255, 255]

    height, width = img.shape[:2]
    # markers = np.zeros(img.shape[:2], np.int32)
    # new_hsv = cv2.inRange(hsv, np.array([20, 20, 100]), np.array([60, 150, 255]))

    seed = (int(width * 0.4), int(height * 0.7))
    cv2.floodFill(flooded, mask, seed, (255, 0, 0), loDiff=(255, 255, 255, 255), upDiff=(255, 255, 255, 255))

    indices = np.where(flooded == (255, 0, 0))
    warp = persp_warp(img, indices)
    cv2.imwrite("/home/algy/cvd/mask.jpg", mask)
    cv2.imwrite("/home/algy/cvd/a.jpg", warp)
