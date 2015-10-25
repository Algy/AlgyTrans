#!/usr/bin/env python

import sys
import numpy as np
import cv2

from persp import totori_affine_wrap

if __name__ == '__main__':
    src = sys.argv[1]
    img = cv2.imread(src)


    cannied = cv2.Canny(img, 40, 80)
    cannied = cv2.GaussianBlur(cannied, (15, 15), 0)

    mask = cv2.copyMakeBorder(cannied, 1, 1, 1, 1, cv2.BORDER_REPLICATE)

    height, width = img.shape[:2]
    flooded = np.zeros((height, width), np.uint8)
    hsv = cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    pinpoint = cv2.inRange(hsv, np.array([20, 20, 100]), np.array([60, 150, 255]))

    pinpoint = cv2.subtract(pinpoint, cannied)


    seed = (int(width * 0.4), int(height * 0.65))   
    cv2.floodFill(flooded, mask, seed, 255, loDiff=255, upDiff=255)

    coord = np.where(flooded != 0)[::-1] # (y, x) -> (x, y)
    indices = np.transpose(coord)
    warp = totori_affine_wrap(img, indices)


    _, warp = cv2.threshold(cv2.cvtColor(warp, cv2.COLOR_BGR2GRAY), 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel = np.ones((2, 2), np.uint8)
    warp = cv2.morphologyEx(warp, cv2.MORPH_OPEN, kernel)

    cv2.imwrite("/home/algy/cvd/pinpoint.jpg", pinpoint)
    cv2.imwrite("/home/algy/cvd/flooded.jpg", flooded)
    cv2.imwrite("/home/algy/cvd/text.jpg", warp)
