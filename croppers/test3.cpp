#include <cstdlib>
#include <map>
#include <iostream>
#include <algorithm>
#include <vector>
#include <opencv2/core/core.hpp>
#include <opencv2/imgproc/imgproc.hpp>
#include <opencv2/photo/photo.hpp>
#include <opencv2/features2d/features2d.hpp>
#include <opencv2/objdetect/objdetect.hpp>
#include <opencv2/highgui/highgui.hpp>
#include <opencv2/ml/ml.hpp>
#define FLOODFILL_MAGIC 1

using namespace std;
class Filler {
public:
    cv::Mat mask;
    vector<cv::Point> resultPoints;
    vector<cv::Point> resultBoxes;
private:
    cv::Mat pinpointImg;
    cv::Mat img;
    cv::Mat canniedImg;
    int inc;
private:
    void makeMask();
    void iterPinpoint(int x, int y);
    inline bool loopFloodFill(int magic, cv::Rect rect, vector<cv::Point>& vecOut);
    inline bool iterFloodFill(int x, int y, int magic, vector<cv::Point>& vecOut);
public:
    Filler(cv::Mat img, cv::Mat pinpointImg, cv::Mat canniedImg);
    void fill();
};

Filler::Filler(cv::Mat img, cv::Mat pinpointImg, cv::Mat canniedImg)
    : img(img),
      pinpointImg(pinpointImg),
      canniedImg(canniedImg),
      inc(0) {
}

void Filler::makeMask() {
    cv::copyMakeBorder(canniedImg, mask, 1, 1, 1, 1, cv::BORDER_CONSTANT, cv::Scalar(255));
    cv::imwrite("/home/algy/cvd/mask_initial.jpg", mask);
}

void Filler::fill() {
    int x, y;
    int result = 0;

    makeMask();

    int height = img.size().height,
        width = img.size().width;

    int cell_height = height / 50,
        cell_width = width / 50;
    for (x = width % cell_width / 2; x < width; x += cell_width) {
        for (y = height % cell_height / 2; y < height; y += cell_height) {
            if (pinpointImg.at<uchar>(y, x) == 0)
                continue;
            iterPinpoint(x, y);
        }
    }
}


inline bool Filler::iterFloodFill(int x, int y, int magic, vector<cv::Point>& vecOut) {
    if (mask.at<uchar>(y + 1, x + 1) == magic) {
        vecOut.push_back(cv::Point(x, y));
        return true;
    }
    return false;
}

inline bool Filler::loopFloodFill(int magic, cv::Rect rect, vector<cv::Point>& indices) {
    cerr << "EXTRACTING POINTS " << magic << endl;

    bool entered = false;
    int x, k;
    const int sx = rect.x, sy = rect.y;
    int right = rect.x + rect.width;
    int bottom = rect.y + rect.height;


    // plus diag
    for (k = sx + sy; k < right + bottom; k++) {
        int xlimit = min(k, right - 1) + 1;
        for (x = max(sx, k - bottom + 1); x < xlimit; x++) {
            if (iterFloodFill(x, k - x, magic, indices)) {
                entered = true;
                goto pldiag;
            }
        }
    }
pldiag:
    // fast continue
    if (!entered) {
        return false;
    }

    int diff = sx - sy;
    for (k = diff + (rect.width - 1); k >= diff - (rect.height - 1); k--) {
        int xlimit = min(bottom + k, right);
        for (x = max(sx, k); x < xlimit; x++) {
            if (iterFloodFill(x, x - k, magic, indices))
                goto midiag;
        }
    }
midiag:
    for (k = right + bottom - 1; k >= sx + sy; k--) {
        int xlimit = min(k, right - 1) + 1;
        for (x = max(sx, k - bottom + 1); x < xlimit; x++) {
            if (iterFloodFill(x, k - x, magic, indices))
                goto pldiag_reverse;
        }
    }
pldiag_reverse:
    for (k = diff - (rect.height - 1); k <= diff + (rect.width - 1); k++) {
        int xlimit = min(bottom + k, right);
        for (x = max(sx, k); x < xlimit; x++) {
            if (iterFloodFill(x, x - k, magic, indices))
                goto midiag_reverse;
        }
    }
midiag_reverse:
    return true;
}

void Filler::iterPinpoint(int x, int y) {
    int idx;
    uchar maskPixel = mask.at<uchar>(y + 1, x + 1);
    if (maskPixel != 0)
        return;

    if (FLOODFILL_MAGIC + inc == 255) {
        cerr << "Warnning: Too many pinpointed areas" << endl;
        makeMask();
        inc = 0;
    }
    int magic = FLOODFILL_MAGIC + inc;
    // int flags = 4 | cv::FLOODFILL_MASK_ONLY | magic << 8;
    int flags = 4;
    cerr << "FLOOD FILLING " << inc << endl;
    
    cv::Rect boundingBox;
    long long area = (int)cv::floodFill(mask, cv::Point(x + 1, y + 1), magic,
        &boundingBox, cv::Scalar(0), cv::Scalar(0), flags);
    inc++;
    
    int height = img.size().height,
        width = img.size().width;
    long long origArea = width * height;

    if (!(origArea * 3LL / 1000LL <= area && area <= origArea * 45LL / 100LL))
        return;

    vector<cv::Point> indices;
    int k, sx, sy;
    int klimit;
    if (!loopFloodFill(magic, boundingBox, indices)) {
        return;
    }
    if (indices.size() < 4 || indices[0] == indices[1]) {
        return;
    }

    resultPoints.push_back(cv::Point(x, y));
    for (idx = 0; idx < 4; idx++) {
        resultBoxes.push_back(indices[idx]);
    }

}

int main (int argc, char** argv) {
    if (argc < 2) {
        cerr << "./program image" << endl;
        return 1;
    }
    char *filename = argv[1];
    int idx, kdx;

    cv::Mat img = cv::imread(filename);

    if (img.data == NULL) {
        cerr << "Cannot read input image" << endl;
        return 1;
    }
    cv::Mat canniedImg;
    cerr << "Cannying" << endl;
    cv::Canny(img, canniedImg, 20, 40);
    cerr << "Done" << endl;
    cv::imwrite("/home/algy/cvd/canny_orig.jpg", canniedImg);
        
    cerr << "Blurring" << endl;
    cv::GaussianBlur(canniedImg, canniedImg, cv::Size(5, 5), 0);
    cv::threshold(canniedImg, canniedImg, 0, 255, cv::THRESH_BINARY);
    {
        cv::Mat element = cv::getStructuringElement(cv::MORPH_RECT, cv::Size(3, 3), cv::Point(1, 1));
        cv::dilate(canniedImg, canniedImg, element);
    }
    cerr << "Done" << endl;
    cv::imwrite("/home/algy/cvd/canny.jpg", canniedImg);

    cv::Mat hsvImg;
    cv::Mat pinpointImg;
    cerr << "Pinpointing" << endl;
    cv::cvtColor(img, hsvImg, cv::COLOR_BGR2HSV);
    cv::inRange(hsvImg,
        cv::Scalar(20, 20, 100),
        cv::Scalar(60, 150, 255),
        pinpointImg);
    cv::subtract(pinpointImg, canniedImg, pinpointImg);
    cerr << "Done" << endl;
    cv::imwrite("/home/algy/cvd/pinpoint.jpg", pinpointImg);

    Filler filler(img, pinpointImg, canniedImg);
    filler.fill();

    map<uchar, cv::Vec3b> colorCache;
    for (int y = 0; y < img.size().height; y++) {
        for (int x = 0; x < img.size().width; x++) {
            uchar val = filler.mask.at<uchar>(y + 1, x + 1);
            if (val != 0) {
                cv::Vec3b &b = img.at<cv::Vec3b>(y, x);
                if (colorCache.find(val) == colorCache.end()) {
                    cv::Vec3b color(rand() % 255, rand() % 255, rand() % 255);
                    colorCache[val] = color;
                }
                b = colorCache[val];
            }
        }
    }
    size_t length = filler.resultPoints.size();
    cout << length << endl << endl;
    for (idx = 0; idx < length; idx++) {
        cv::Point pnt = filler.resultPoints[idx];
        cout << "[" << pnt.x << ", " << pnt.y << "]" << endl;

        cv::circle(img, pnt, 3, cv::Scalar(0, 0, 255), 3);
        for (kdx = 0; kdx < 4; kdx++) {
            cv::Point rectPnt = filler.resultBoxes[idx * 4 + kdx];
            cout << rectPnt.x << " " << rectPnt.y << endl;

            cv::line(img,
                filler.resultBoxes[idx * 4 + kdx],
                filler.resultBoxes[idx * 4 + (kdx + 1)%4],
                cv::Scalar(0, 255, 0),
                3);
        }
        cout << endl << endl;
    }
    cv::imwrite("/home/algy/cvd/a.jpg", img);
    return 0;
}
