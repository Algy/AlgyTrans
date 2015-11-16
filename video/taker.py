#!/usr/bin/env python
import os
import sys
import time
import signal
import atexit
import cv2
import numpy as np
import picamera

from subprocess import Popen
from threading import Lock, Thread

FILE_PATH = '/dev/shm/arand/mn.jpg'
CANNY_FILE_PATH = '/dev/shm/arand/mn_canny.jpg'

CURRENT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))

def canny_work(canny_level, blur_size, kernel_size):
    return Popen(["python", os.path.join(CURRENT_DIRECTORY, "canny.py"),
                  FILE_PATH,
                  CANNY_FILE_PATH,
                  str(canny_level),
                  str(blur_size),
                  str(kernel_size)])


class PictureTaker(object):
    def __init__(self, canny_level=80, blur_size=0, kernel_size=1):
        self.canny_level = canny_level
        self.kernel_size = kernel_size
        self.blur_size = blur_size
        self.canny_lock = Lock()
        self.stop_thread = False
        self.thread = None

        try:
            os.mkdir(os.path.dirname(FILE_PATH))
        except:
            pass
        atexit.register(self._cleanup_at_exit)

    def set_canny(self, canny_level, blur_size, kernel_size):
        with self.canny_lock:
            self.canny_level = canny_level
            self.blur_size = blur_size
            self.kernel_size = kernel_size
            
    def _cleanup_at_exit(self):
        print "ByeBye"
        self.stop_thread = False
        if self.thread:
            print "Joining thread"
            self.thread.join()

    def take(self, camera):
        N = 32
        start = time.time()
        for _ in range(N):
            if self.stop_thread:
                break
            camera.capture(FILE_PATH + ".tmp.jpg", use_video_port=True)
            os.rename(FILE_PATH + ".tmp.jpg", FILE_PATH)
        sys.stderr.write('[Raspistill] Captured %d images at %.2ffps\n' % (N, N / (time.time() - start)))

    def thread_work(self):
        with picamera.PiCamera() as camera:
            camera.resolution = (1200, 800)
            while not self.stop_thread:
                self.take(camera)
                canny_work(
                    self.canny_level,
                    self.blur_size,
                    self.kernel_size
                )

    def start_thread(self):
        thread = Thread(target=self.thread_work)
        thread.daemon = True
        thread.start()
        self.thread = thread
