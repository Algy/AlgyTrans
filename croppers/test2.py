#!/usr/bin/env python

import sys
import numpy as np
import cv2

print "MODULE LOADED"
class Cluster(object):
    def __init__(self, pts, builder): 
        self.builder = builder
        self.pts = pts

    def points(self):
        return self.pts

    def area(self):
        return float(len(self.pts)) / self.builder.NUM_X / self.builder.NUM_Y

    def density(self):
        num = 2 * self.builder.eps + 1
        return float(len(self.pts)) / num / num

    def bounding_box(self):
        return (min(self.pts, key=lambda (x, _): x)[0],
                min(self.pts, key=lambda (_, y): y)[1],
                max(self.pts, key=lambda (x, _): x)[0],
                max(self.pts, key=lambda (_, y): y)[1])

    def crop(self, img):
        x1, y1, x2, y2 = self.bounding_box()
        '''
        x1 = max(x1 - self.builder.cell_width, 0)
        x2 = min(x2 + self.builder.cell_width, self.builder.width - 1)
        y1 = max(y1 - self.builder.cell_height, 0)
        y2 = min(y2 + self.builder.cell_height, self.builder.height - 1)
        '''
        return img[y1:(y2+1), x1:(x2+1)]

    def ratio(self):
        x1, y1, x2, y2 = self.bounding_box()
        if x1 == x2 and y1 == y2:
            return None
        elif x1 == x2:
            return None
        else:
            return float(y2 - y1) / (x2 - x1)

        
class GridClusterBuilder(object):
    def __init__(self, eps, min_pts, NUM_X=50, NUM_Y=50):
        self.eps = eps
        self.min_pts = min_pts
        self.NUM_X = NUM_X
        self.NUM_Y = NUM_Y

        self.width = None
        self.height = None
        self.cell_height = None
        self.cell_width = None

    def _range(self):
        width, height = self.width, self.height
        cell_width, cell_height = self.cell_width, self.cell_height

        off_y = height % cell_height / 2
        off_x = width % cell_width / 2
        for ydx in range(self.NUM_Y):
            center_y = cell_height * ydx + off_y
            if center_y >= self.height:
                continue
            for xdx in range(self.NUM_X):
                center_x = cell_width * xdx + off_x
                if center_x >= self.width:
                    continue
                yield (center_x, center_y)

    def _cell_range(self, pt):
        for y in range(pt[1] - self.eps * self.cell_height,
                       pt[1] + self.eps * self.cell_height + 1,
                       self.cell_height):
            if y < 0 or y >= self.height:
                continue
            for x in range(pt[0] - self.eps * self.cell_width,
                           pt[0] + self.eps * self.cell_width + 1,
                           self.cell_width):
                if x < 0 or x >= self.width:
                    continue
                yield (x, y)

    def draw(self, img, color=(0, 0, 256)):
        for pt in self._range():
            cv2.circle(img, pt, 2, color)

    def _expand(self, img, seed, cluster_pts, visited):
        pts_len = sum(int(img[y, x] > 0) for x, y in self._cell_range(seed))
        if pts_len >= self.min_pts:
            cluster_pts.append(seed)
            visited.add(seed)
            for new_seed in self._cell_range(seed):
                if new_seed not in visited:
                    self._expand(img, new_seed, cluster_pts, visited)

    def build(self, img, low_ratio=0, high_ratio=15, low_area=0, high_area=1):
        self.height, self.width = img.shape
        self.cell_width = self.width / self.NUM_X
        self.cell_height = self.height / self.NUM_Y

        visited = set()
        result = []
        for x, y in self._range():
            if (x, y) in visited:
                continue
            if img[y, x] > 0:
                # try expanding
                cluster_pts = [(x, y)]
                visited.add((x, y))
                self._expand(img, (x, y), cluster_pts, visited)
                cluster = Cluster(cluster_pts, self)
                ratio = cluster.ratio()
                area = cluster.area()
                if len(cluster_pts) > 1:
                    print "MET cluster(area=%.2f, ratio=%s, pts=%d)"%(area,
                                                                      ("%.2f"%ratio)
                                                                        if ratio is not None
                                                                        else ratio,
                                                                      len(cluster_pts))

                if low_area <= cluster.area() <= high_area and \
                   ratio is not None and \
                   low_ratio <= ratio <= high_ratio:
                    result.append(cluster)
        return result
    
if __name__ == '__main__':
    try:
        src = sys.argv[1]
        dest = sys.argv[2]
    except IndexError:
        print "Usage: ./test.py src_img dest_img"
        sys.exit(1)
    img = cv2.imread(src)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    kernel = np.ones((10, 10), np.uint8)

    normal_canny = cv2.Canny(img.copy(), 60, 60)
    cv2.imwrite("/home/algy/cvd/nc.jpg", normal_canny)
    hough = normal_canny.copy()
    lines = cv2.HoughLines(hough, 10, np.pi / 180, 300)
    
    if lines is not None:
        for rho, theta in lines[0]:
            a = np.cos(theta)
            b = np.sin(theta)
            x0 = a*rho
            y0 = b*rho
            x1 = int(x0 + 1000*(-b))   # Here i have used int() instead of rounding the decimal value, so 3.8 --> 3
            y1 = int(y0 + 1000*(a))    # But if you want to round the number, then use np.around() function, then 3.8 --> 4.0
            x2 = int(x0 - 1000*(-b))   # But we need integers, so use int() function after that, ie int(np.around(x))
            y2 = int(y0 - 1000*(a))

            cv2.line(img, (x1, y1), (x2, y2), (0, 255, 0), 1)

    new_hsv = cv2.inRange(hsv, np.array([20, 20, 160]), np.array([60, 255, 255]))
    cv2.imwrite("/home/algy/cvd/threshold.jpg", new_hsv)
    new_hsv = cv2.morphologyEx(new_hsv, cv2.MORPH_OPEN, kernel)
    cv2.imwrite("/home/algy/cvd/open.jpg", new_hsv)

    builder = GridClusterBuilder(eps=1, min_pts=7)
    clusters = builder.build(new_hsv, low_ratio=0.2, high_ratio=0.8, low_area=0.02, high_area=0.45)

    colors = [(0, 0, 255), (0, 255, 0), (255, 255, 0), (0, 255, 255), (255, 0, 255)]
    for idx, cluster in enumerate(clusters):
        color = colors[idx % len(colors)]
        for pt in cluster.points():
            cv2.circle(img, pt, 2, color)
        x1, y1, x2, y2 = cluster.bounding_box()
        cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 0), 3)
        cv2.imwrite("/home/algy/cvd/cluster_%d.jpg"%idx, img)

        st_x, st_y, _, _ = cluster.bounding_box()
        cropped = cluster.crop(new_hsv)
        cropped = cv2.Canny(cropped, 70, 150)
        cv2.imwrite("/home/algy/cvd/canny_%d.jpg"%idx, cropped)
        cropped = cv2.GaussianBlur(cropped, (15, 15), 0)
        cv2.imwrite("/home/algy/cvd/blurred_%d.jpg"%idx, cropped)
    cv2.imwrite(dest, img)
