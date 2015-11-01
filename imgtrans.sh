#!/bin/bash

convert $1 /tmp/example.ppm
$(dirname $0)/nhocr -o - -block /tmp/example.ppm | $(dirname $0)/trans.py

