#!/usr/bin/env python
import os
import sys
import time
import signal
import atexit
import cv2
import numpy as np

from threading import Lock, Thread
from subprocess import Popen, PIPE


OPTIONS = ["-w", "1200",
           "-h", "800",
           "-t", "0",
           "-v",
           "-ss", "128000",
           "-ISO", "100",
           "--sharpness", "100",
           ]
FILE_PATH = '/dev/shm/arand/mn.jpg'
CANNY_FILE_PATH = '/dev/shm/arand/mn_canny.jpg'


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
        self.proc = Popen(["raspistill", "-o", FILE_PATH, "--signal"] + OPTIONS,
                          stderr=PIPE)
        atexit.register(self._cleanup_at_exit)

    def set_canny(self, canny_level, blur_size, kernel_size):
        with self.canny_lock:
            self.canny_level = canny_level
            self.blur_size = blur_size
            self.kernel_size = kernel_size
            
    def _cleanup_at_exit(self):
        print "ByeBye"
        self.proc.send_signal(signal.SIGINT)
        time.sleep(1)
        if self.proc.poll() is None:
            try:
                self.proc.kill()
                print "Raspistill Process killed"
            except OSError:
                pass
        self.stop_thread = False
        if self.thread:
            print "Joining thread"
            self.thread.join()

    def take(self):
        try:
            mtime = os.path.getmtime(FILE_PATH)
        except OSError:
            mtime = None
        self.proc.send_signal(signal.SIGUSR1)
        while True:
            try:
                if os.path.getmtime(FILE_PATH) != mtime:
                    break
            except OSError:
                pass
            time.sleep(0.1)

    def thread_work(self):
        while not self.stop_thread:
            line = self.proc.stderr.readline()
            if not line:
                break
            sys.stderr.write("[ImageTaker] ")
            sys.stderr.write(line)
            if "SIGUSR1" in line and "wait" in line.lower():
                self.take()
                img = cv2.imread(FILE_PATH)
                img = cv2.Canny(img, self.canny_level, self.canny_level)
                if self.blur_size > 0:
                    img = cv2.GaussianBlur(img, (self.blur_size * 2 + 1, self.blur_size * 2 + 1), 0)
                    _, img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY)
                if self.kernel_size > 0:
                    kernel = cv2.getStructuringElement(
                        cv2.MORPH_ELLIPSE,
                        (self.kernel_size * 2 + 1,
                         self.kernel_size * 2 + 1),
                        (self.kernel_size, self.kernel_size));
                    img = cv2.dilate(img, kernel)
                cv2.imwrite(CANNY_FILE_PATH, img)
                del img

    def start_thread(self):
        thread = Thread(target=self.thread_work)
        thread.daemon = True
        thread.start()
        self.thread = thread
