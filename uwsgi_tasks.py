import time

from app import picture_taker
from uwsgidecorators import rbtimer, filemon, postfork


@postfork
def taker():
    picture_taker.start_thread()
