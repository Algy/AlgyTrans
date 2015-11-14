#!/usr/bin/env python
# coding: utf-8

import sys
import os
import uuid
import flask as fl
import numpy as np
import cv2

from tempfile import NamedTemporaryFile
from flask import request
from trans import build_trans
from corrector import correct
from subprocess import Popen, PIPE, check_output
from video.taker import PictureTaker, FILE_PATH, CANNY_FILE_PATH
from croppers.persp import persp_warp, order_points

from config import IMAGE_TEMP_PATH

CURRENT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
ja_ko_translator = build_trans()

app = application = fl.Flask(__name__)
app.debug = True
picture_taker = PictureTaker()

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

 
@app.route("/")
def index():
    return fl.render_template("index.html")

@app.route("/canny", methods=['GET', 'POST'])
def canny():
    if request.method == 'POST':
        json = request.get_json()
        try:
            canny_level = int(json.get("canny_level", picture_taker.canny_level))
            blur_size = int(json.get("blur_size", picture_taker.blur_size))
            kernel_size = int(json.get("kernel_size", picture_taker.kernel_size))
        except ValueError:
            fl.abort(400)
        picture_taker.set_canny(canny_level, blur_size, kernel_size)

    return fl.jsonify(
        url="/mn_canny.jpg",
        canny_level=picture_taker.canny_level,
        blur_size=picture_taker.blur_size,
        kernel_size=picture_taker.kernel_size,
    )


@app.route("/floodfill", methods=['POST'])
def floodfill():
    json = request.get_json()
    try:
        point = json["point"]
        assert (len(point) == 2 and
                all(isinstance(n, (int, long))
                    for n in point))
    except (TypeError, KeyError, ValueError, AssertionError):
        fl.abort(400)

    argv = [os.path.join(CURRENT_DIRECTORY,
                         "croppers",
                         "detector.out"),
            "--input", FILE_PATH,
            "--canny-input", CANNY_FILE_PATH,
            "--pinpoint-range", "255,255,255:255,255,255",
            "--seed-point", ",".join(str(n) for n in point)]
    buf = check_output(argv)
    rects = parse_detector_output(buf)

    return fl.jsonify(
        rects=map(lambda x: x.tolist(), rects)
    )


@app.route("/warp", methods=['POST'])
def warp():
    '''
    Input -
        rect: ...,
        rotation: <degrees>,
        threshold: {
            method: "naive", "otsu" or "adaptive"
            value: float or {C: int, block_size: int}
        }

    Output -
        warp_id: ...,
        url: ""

    '''
    json = request.get_json()
    try:
        for pt in json["rect"]:
            assert (len(pt) == 2)
            for n in pt:
                int(n)
        rect = np.array(json["rect"])
        rot_deg = float(json.get("rotation", 0))
        threshold = json["threshold"]
        thr_method = threshold["method"]
        thr_value = threshold.get("value")
        if ((thr_method == 'naive' or thr_method == 'adaptive') and
            thr_value is None):
            raise ValueError
    except (TypeError, KeyError, ValueError, AssertionError):
        fl.abort(400)

    warp_id = uuid.uuid4().hex
    img = cv2.imread(FILE_PATH, flags=cv2.IMREAD_GRAYSCALE)
    img = persp_warp(img, rect)
    height, width = img.shape[:2]

    if rot_deg != 0:
        M = cv2.getRotationMatrix2D((width / 2, height / 2), -rot_deg, 1.0)
        img = cv2.warpAffine(img, M, (width, height))

    try:
        if thr_method in ('naive', 'otsu'):
            thr_type = cv2.THRESH_BINARY_INV
            if thr_method == 'otsu':
                thresh = 255
                thr_type |= cv2.THRESH_OTSU
            else:
                thresh = int(thr_value)

            _, img = cv2.threshold(
                img,
                thresh,
                255,
                thr_type)

        elif thr_method == 'adaptive':
            img = cv2.adaptiveThreshold(
                img,
                255,
                cv2.ADAPTIVE_THRESH_MEAN_C,
                cv2.THRESH_BINARY_INV,
                2 * int(thr_value["block_size"]) + 1,
                int(thr_value["C"]))
        else:
            raise Exception("Not Reachable")
    except (KeyError, ValueError):
        fl.abort(400)
    cv2.imwrite(get_warp_image_path(warp_id), img)

    return fl.jsonify(
        warp_id=warp_id,
        url=fl.url_for("warp_image", pk=warp_id)
    )

def get_warp_image_path(pk):
    return os.path.join(IMAGE_TEMP_PATH, "img", pk + ".jpg")

@app.route("/warp/image/<pk>")
def warp_image(pk):
    return fl.send_file(
        get_warp_image_path(pk),
        cache_timeout=0
    )

@app.route("/warp/<pk>", methods=['DELETE'])
def warp_by_id(pk):
    try:
        os.unlink(get_warp_image_path(pk))
    except OSError:
        return "NoSuchWarp"
    return "Ok"

def none_or_int(val):
    if val is not None:
        return int(val)

@app.route("/ocr/<warp_id>", methods=['POST'])
def ocr(warp_id):
    '''
    Input -
    {
        [crop: {
            [left: int]
            [right: int]
            [top: int]
            [bottom: int]
        }]
    }

    Output -
        content
        translated
    '''

    img_path = get_warp_image_path(warp_id) 
    img = cv2.imread(img_path, flags=cv2.IMREAD_GRAYSCALE)
    if img is None:
        fl.abort(404)

    json = request.get_json()
    try:
        if "crop" in json:
            crop_obj = json["crop"]
            left = none_or_int(crop_obj.get("left"))
            right = none_or_int(crop_obj.get("right"))
            top = none_or_int(crop_obj.get("top"))
            bottom = none_or_int(crop_obj.get("bottom"))
            img = img[top:bottom, left:right]
    except (KeyError, ValueError):
        fl.abort(400)

    with NamedTemporaryFile(suffix='.ppm') as f:
        cv2.imwrite(f.name, img)
        proc = Popen([os.path.join(CURRENT_DIRECTORY, "nhocr"),
                      f.name,
                      "-o",
                      "-",
                      "-block"],
                     stdout=PIPE)
        buf = u"".join([line.decode("utf-8")
                        for line in proc.stdout])
        proc.wait()
    buf = u"\n".join(buf.splitlines())
    content = correct(buf)
    print content.encode("utf-8")
    annotated, translated = ja_ko_translator(content)

    return fl.jsonify(
        content=annotated,
        translated=translated
    )

if __name__ == '__main__':
    app.run(port=5000, host='0.0.0.0')
