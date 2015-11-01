#!/usr/bin/env python
# coding: utf-8
import math
import time
import sys
import numpy as np
import cv2
import argparse

from persp import persp_warp
class Time(object):
    def __init__(self, name):
        self.name = name

    def __enter__(self, *args, **kwds):
        self.ts = time.time()

    def __exit__(self, *args, **kwds):
        print "[%s]Time %.2lfms"%(self.name, (time.time() - self.ts) * 1000)


def parse_detector_output(src):
    lines = src.splitlines()
    length = len(lines)
    idx = 0

    result = []
    while idx < length:
        if lines[idx].startswith("["):
            idx += 1
            last_idx = idx
            while idx < length and not lines[idx].startswith("["):
                idx += 1
            item = np.array(
                map(lambda line:
                      map(int, line.split()),
                    filter(bool,
                           map(lambda x: x.strip(),
                               lines[last_idx:idx]))))
            result.append(item)
        else:
            break
    return result

def avg(list):
    if list:
        return sum(list) / float(len(list))
    else:
        return None

if __name__ == '__main__':
    img = cv2.imread(sys.argv[1])
    for idx, pts in enumerate(parse_detector_output(sys.stdin.read())):
        '''
        lt, _, rb, lb = pts
        # respect bottom edge
        pts[1] = lt + rb - lb
        '''
        warp = persp_warp(img, pts)
        height, width = warp.shape[:2]

        cv2.imwrite("/home/algy/cvd/orig_warp_%d.jpg"%idx, warp)
        warp = cv2.cvtColor(warp, cv2.COLOR_BGR2GRAY)
        warp = cv2.adaptiveThreshold(
            warp,
            255,
            cv2.ADAPTIVE_THRESH_MEAN_C,
            cv2.THRESH_BINARY_INV,
            11,
            3)

        with Time("Remove noise"):
            for offx, arr in ((0, warp[:, :20]), (width - 25, warp[:, -25:])):
                ptlist = np.transpose(np.where(arr)[::-1])
                for x, y in ptlist:
                    x += offx
                    if warp[y, x] != 0:
                        cv2.floodFill(warp, None, (x, y), 0, flags=8)

        # kernel = np.array([[1] * 5 for _ in range(2)], np.uint8)
        # warp = cv2.morphologyEx(warp, cv2.MORPH_OPEN, kernel, iterations=1)

        with Time("Rotation"):
            hough_result = cv2.HoughLinesP(warp.copy(), 1, np.pi / 180, 50, minLineLength=width / 4, maxLineGap=200)
            hough_result = hough_result[0] if hough_result is not None else []
        
            angle = avg([math.atan2(ey - sy, ex - sx) for sx, sy, ex, ey in hough_result])
            if angle:
                degree = angle / np.pi * 180
                print "ANGLE ", degree
                '''
                for sx, sy, ex, ey in hough_result:
                    cv2.line(warp, (sx, sy), (ex, ey), 128, 1)
                '''
                M = cv2.getRotationMatrix2D((width / 2, height / 2), degree, 1.0)
                warp = cv2.warpAffine(warp, M, (width, height))


        with Time("deisolate"):
            mask = warp.copy()
            for x, y in np.transpose(np.where(warp != 0)[::-1]):
                if mask[y, x] != 0:
                    area, (_, _, w, h) = cv2.floodFill(mask, None, (x, y), 0, flags=8)
                    if area < 4: # or w < 5 and h < 5:
                        cv2.floodFill(warp, None, (x, y), 0, flags=8)

        '''
        with Time("Final crop"):
            warp = warp[15:-25, 15:-75]
        '''
        cv2.imwrite("/home/algy/cvd/warp_%d.jpg"%idx, warp)
