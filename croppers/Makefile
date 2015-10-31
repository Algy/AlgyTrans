CCPLUS=clang++
CCFLAGS=-g -std=c++11
LFLAGS=-lopencv_core -lopencv_imgproc -lopencv_highgui -lopencv_ml -lopencv_video -lopencv_features2d -lopencv_calib3d -lopencv_objdetect -lopencv_contrib -lopencv_legacy -lopencv_stitching


all: detector.cpp
	$(CCPLUS) $(CCFLAGS) $(LFLAGS) -o detector.out detector.cpp


clean:
	rm -rf detector.out
