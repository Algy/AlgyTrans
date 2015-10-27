#!/usr/bin/env python
import sys
import numpy as np
import cv2
from persp import totori_affine_wrap


def plus_diag_range(width, height, reverse=False):
    k_range = range(0, width + height)
    if reverse:
        k_range.reverse()
    for k in k_range:
        for x in range(max(0, k - height + 1), min(k, width - 1) + 1):
            y = k - x
            yield (x, y)


def minus_diag_range(width, height, reverse=False):
    diff = max(width, height) - 1
    k_range = range(diff, -diff - 1, -1)
    if reverse:
        k_range.reverse()

    for k in k_range:
        for x in range(max(0, k), min(height + k, width)):
            y = x - k
            yield (x, y)



FLOODFILL_MAGIC = 100
def fill(pinpoint_img, img, cannied):
    '''
    (warpped_img) generator
    '''
    def make_mask():
        mask = cv2.copyMakeBorder(cannied, 1, 1, 1, 1, cv2.BORDER_REPLICATE)
        mask[mask != 0] = 255
        return mask

    mask = make_mask()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    
    height, width = img.shape[:2]
    cell_height, cell_width = height / 50, width / 50
    inc = 0
    pinpoints = [(x, y)
                 for x in xrange(width % cell_width / 2, width, cell_width)
                 for y in xrange(height % cell_height / 2, height, cell_height)
                 if pinpoint_img[y, x] != 0]
    
    length = len(pinpoints)
    for idx, pnt in enumerate(pinpoints):
        if FLOODFILL_MAGIC <= mask[pnt[1] + 1, pnt[0] + 1] < 255:
            continue
        print "%.2lf%%"%(float(idx) / length * 100.)
        magic = FLOODFILL_MAGIC + inc
        flags = 4 | magic << 8 
        print "FLOOD FILLING %d"%inc
        area, (rx, ry, rw, rh) = cv2.floodFill(gray, mask, pnt, 199, loDiff=(9, ), upDiff=(9,), flags=flags)
        print "Done"
        if not (0.003 <= float(area) / width / height <= 0.45):
            continue

        indices = []
        print "EXTRACTING POINTS of %d"%inc
        for fn, reverse in [(plus_diag_range, False),
                            (minus_diag_range, False),
                            (plus_diag_range, True),
                            (minus_diag_range, True)]:
            for dx, dy in fn(rw, rh, reverse=reverse):
                x = rx + dx
                y = ry + dy
                if mask[y + 1, x + 1] == magic:
                    indices.append([x, y])
                    break
        indices = np.array(indices, np.int32)
        for idx in range(-1, len(indices) - 1):
            p1 = indices[idx]
            p2 = indices[idx + 1]
            cv2.line(img, tuple(p1), tuple(p2), (0, 255, 0), 2)

        print "EXTRACTING DONE %d, %s"%(inc, repr(indices))
        cv2.imwrite("/home/algy/cvd/flooded_%d.jpg"%inc, gray)
        warp = totori_affine_wrap(img, indices, minus_one=True)
        inc += 1
        if FLOODFILL_MAGIC + inc == 255:
            mask = make_mask()
            inc = 0
        yield warp


if __name__ == '__main__':
    src = sys.argv[1]
    img = cv2.imread(src)


    print "Cannying..."
    cannied = cv2.Canny(img, 20, 40)
    print "Done..."
    print "Blurring..."
    cannied = cv2.GaussianBlur(cannied, (5, 5), 0)
    cannied[cannied != 0] = 255
    x = cv2.adaptiveThreshold(cannied, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 7, -64)
    cannied = cv2.add(cannied, x)
    print "Done..."
    cv2.imwrite("/home/algy/cvd/canny.jpg", cannied)

    height, width = img.shape[:2]
    hsv = cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
    print "Pinpointing..."
    pinpoint_img = cv2.inRange(hsv, np.array([20, 20, 100]), np.array([60, 150, 255]))
    print "Done..."

    print "Subtracting..."
    pinpoint_img = cv2.subtract(pinpoint_img, cannied)
    print "Done..."

    for idx, warp in enumerate(fill(pinpoint_img, img, cannied)):
        cv2.imwrite("/home/algy/cvd/warp_%d.jpg"%idx, warp)
        tb, bb = int(warp.shape[0] * .114), int(warp.shape[0] * 0.886)
        lb, rb = int(warp.shape[1] * 0.011), int(warp.shape[1] * 0.924)
        if lb >= rb or tb >= bb:
            continue
        warp = warp[tb:bb, lb:rb]
        gray_warp = cv2.cvtColor(warp, cv2.COLOR_BGR2GRAY)
        print "Thresholding..."
        _, warp = cv2.threshold(gray_warp,
                                0,
                                255,
                                cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        print "Done..."
        kernel = np.ones((2, 2), np.uint8)
        print "Morphing..."
        warp = cv2.morphologyEx(warp, cv2.MORPH_OPEN, kernel)
        print "Done..."
        cv2.imwrite("/home/algy/cvd/text_%d.jpg"%idx, warp)
        print "IDX %d"%idx
    cv2.imwrite("/home/algy/cvd/pinpoint.jpg", pinpoint_img)
    cv2.imwrite("/home/algy/cvd/a.jpg", img)
