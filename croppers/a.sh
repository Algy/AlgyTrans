#!/bin/sh
x=$1
input=~/cvd/totori-samples/objects/s$x.jpg
./detector.out --input $input --dbg-canny-image ~/cvd/canny.jpg --kernel-size 1 --blur-size 0 --grid-count 10 --dbg-image ~/cvd/a.jpg | ./threshold.py $input
