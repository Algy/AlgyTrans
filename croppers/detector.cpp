#include <cstdlib>
#include <getopt.h>

#include <string>
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

class Config {
private:
    vector<string> optNames;
    map<string, string*> optNameStrRefMap; // long name -> string *
    map<string, int*> optNameIntRefMap; // long name -> int *
    map<string, bool*> optNameBoolRefMap; // long name -> bool *
    map<string, double*> optNameDoubleRefMap; // long name -> double *
    map<string, string> optNameDescMap; // long name -> description
    vector<struct option> optStructs;
    bool optPadded = false;
private:
    bool _addOpt(string& name, int has_arg, string& desc) {
        if (optPadded) {
            return false;
        }
        optNames.push_back(name);
        optStructs.push_back((struct option){optNames.back().c_str(), has_arg, 0, 0});
        optNameDescMap[name] = desc;
        return true;
    }

    bool addOpt(string name, int has_arg, string desc, string* ref) {
        if (!_addOpt(name, has_arg, desc))
            return false;
        optNameStrRefMap[name] = ref;
        return true;
    }

    bool addOpt(string name, int has_arg, string desc, int* ref) {
        if (!_addOpt(name, has_arg, desc))
            return false;
        optNameIntRefMap[name] = ref;
        return true;
    }

    bool addOpt(string name, int has_arg, string desc, bool* ref) {
        if (!_addOpt(name, has_arg, desc))
            return false;
        optNameBoolRefMap[name] = ref;
        return true;
    }

    bool addOpt(string name, int has_arg, string desc, double* ref) {
        if (!_addOpt(name, has_arg, desc))
            return false;
        optNameDoubleRefMap[name] = ref;
        return true;
    }

    bool postParse();
    bool parseOpt(int argc, char** argv) {
        if (!optPadded) {
            optPadded = true;
            optStructs.push_back((struct option){0, 0, 0, 0});
        }
        struct option *options = optStructs.data();
        int ind;
        int c;
        while ((c = getopt_long_only(argc, argv, "", options, &ind)) != -1) {
            if (c == '?') {
                printOpt(argv[0]);
                return false;
            }
            string name = options[ind].name;

            if (optNameIntRefMap.find(name) != optNameIntRefMap.end()) {
                int* ref = optNameIntRefMap[name];
                *ref = atoi(optarg);
            } else if (optNameStrRefMap.find(name) != optNameStrRefMap.end()) {
                string* ref = optNameStrRefMap[name];
                *ref = optarg;
            } else if (optNameBoolRefMap.find(name) != optNameBoolRefMap.end()) {
                bool* ref = optNameBoolRefMap[name];
                string optArg = optarg;
                if (optArg == "y" || optArg == "yes" || optArg == "t" || optArg == "true" || optArg == "1") {
                    *ref = true;
                } else {
                    *ref = false;
                }
            } else if (optNameDoubleRefMap.find(name) != optNameDoubleRefMap.end()) {
                *optNameDoubleRefMap[name] = atof(optarg);
            }
            if (!postParse())
                return false;
        }
        return true;
    }

    void printOpt(const char* arg0) {
        cerr << arg0 << " ";
        for (int idx = 0; idx < optStructs.size(); idx++) {
            struct option opt = optStructs[idx];
            if (!opt.name)
                break;
            cerr << "[--" << opt.name << "] ";
        }
        cerr << endl;
        cerr << "--------" << endl << "Usage" << endl << endl;

        for (int idx = 0; idx < optStructs.size(); idx++) {
            struct option *opt = &optStructs[idx];
            if (!opt->name)
                break;
            cerr << "--" << opt->name << ": ";
            cerr << optNameDescMap[string(opt->name)] << endl;
        }
    }

public:
    string imageFilename;
    int cannyLevel = 40;
    int blurSize = 2;
    int kernelSize = 1;
    int gridCount = 50;

    double maxRectRatio = 1.6;
    
    string _pinpointStr;
    cv::Scalar pinpointBegin = cv::Scalar(20, 20, 100);
    cv::Scalar pinpointEnd = cv::Scalar(60, 150, 255);

    bool verbose = false;

    string dbgFilename;
    string dbgPinpointFilename;
    string dbgCannyFilename;
public:
    Config() {
        addOpt("input", required_argument, "File name. If not specified, program reads an image from stdin", &this->imageFilename);
        addOpt("canny-level", required_argument, "Canny level", &this->cannyLevel);
        addOpt("blur-size", required_argument, "Size of kernel used in the gaussian blur phase", &this->blurSize);
        addOpt("kernel-size", required_argument, "Size of kernel used in the dilate phase", &this->kernelSize);
        addOpt("grid-count", required_argument, "Count of grid edges in an axis", &this->gridCount);
        addOpt("pinpoint-range", required_argument, "Pinpoint range in HSV color space (e.g 20,20,100:60,150,255)", &this->_pinpointStr);
        addOpt("max-rect-ratio", required_argument, "Rect ratio", &this->maxRectRatio);
        addOpt("verbose", required_argument, "Verbose mode", &this->verbose);
        addOpt("dbg-image", required_argument, "Path to which image footprint will be saved", &this->dbgFilename);
        addOpt("dbg-pinpoint-image", required_argument, "", &this->dbgPinpointFilename);
        addOpt("dbg-canny-image", required_argument, "", &this->dbgCannyFilename);
    }

    void loadFromArgv(int argc, char **argv) {
        if (!parseOpt(argc, argv)) {
            printOpt(argv[0]);
            exit(1);
        }
    }

    void log(string msg) {
        if (verbose)
            cerr << msg << endl;
    }

} config;

bool Config::postParse() {
    if (_pinpointStr == "") {
        return true;
    }

    size_t idx = _pinpointStr.find(":");
    if (idx == _pinpointStr.npos) {
        return false;
    }

    string before = _pinpointStr.substr(0, idx);
    string after = _pinpointStr.substr(idx + 1);

    for (int k = 0; k <= 1; k++) {
        cv::Scalar& dest = k == 0? pinpointBegin : pinpointEnd;
        string& line = k == 0? before : after;

        int cnt = 0;
        int values[3];
        int lastidx = 0;
        int idx;
        while (cnt < 3) {
            idx = line.find(",", lastidx);
            string part = line.substr(lastidx, idx - lastidx);
            lastidx = idx + 1;
            values[cnt++] = atoi(part.c_str());
            if (idx == line.npos) {
                break;
            }
        }
        if (cnt < 3 || idx != line.npos) {
            return false;
        }
        dest = cv::Scalar(values[0], values[1], values[2]);
    }
    _pinpointStr = "";
    return true;
}

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
}

void Filler::fill() {
    int x, y;
    int result = 0;

    makeMask();

    int height = img.size().height,
        width = img.size().width;

    int cell_height = max(height / config.gridCount, 1),
        cell_width = max(width / config.gridCount, 1);
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
    config.log("EXTRACTING POINTS");

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
        for (x = max(sx, k + sy); x < xlimit; x++) {
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
        for (x = max(sx, k + sy); x < xlimit; x++) {
            if (iterFloodFill(x, x - k, magic, indices))
                goto midiag_reverse;
        }
    }
midiag_reverse:
    return true;
}

/*
inline bool Filler::loopFloodFill(int magic, cv::Rect rect, vector<cv::Point>& indices) {
    const int sx = rect.x, sy = rect.y;
    int right = rect.x + rect.width;
    int bottom = rect.y + rect.height;
    bool entered = false;

    int x, y;
    for (x = sx; x < right; x++) {
        for (y = sy; y < bottom; y++) {
            if (iterFloodFill(x, y, magic, indices)) {
                entered = true;
                goto left;
            }
        }
    }
left:
    if (!entered)
        return false;
    for (y = sy; y < bottom; y++) {
        for (x = sx; x < right; x++) {
            if (iterFloodFill(x, y, magic, indices)) {
                goto top;
            }
        }
    }
top:
    for (x = right - 1; x >= sx; x--) {
        for (y = sy; y < bottom; y++) {
            if (iterFloodFill(x, y, magic, indices)) {
                goto right;
            }
        }
    }
right:
    for (y = bottom - 1; y >= sy; y--) {
        for (x = sx; x < right; x++) {
            if (iterFloodFill(x, y, magic, indices)) {
                goto bottom;
            }
        }
    }
bottom:
    return true;
}
*/

void Filler::iterPinpoint(int x, int y) {
    int idx;
    uchar maskPixel = mask.at<uchar>(y + 1, x + 1);
    if (maskPixel != 0)
        return;

    if (FLOODFILL_MAGIC + inc == 255) {
        config.log("Warnning: Too many pinpointed areas");
        makeMask();
        inc = 0;
    }
    int magic = FLOODFILL_MAGIC + inc;
    // int flags = 4 | cv::FLOODFILL_MASK_ONLY | magic << 8;
    int flags = 4;
    config.log("FLOOD FILLING");
    
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
    if (cv::norm(indices[0] - indices[1]) > cv::norm(indices[1] - indices[2])) {
        cv::Point tmp = indices[0];
        indices[0] = indices[1];
        indices[1] = indices[2];
        indices[2] = indices[3];
        indices[3] = tmp;
    }


    resultPoints.push_back(cv::Point(x, y));
    for (idx = 0; idx < 4; idx++) {
        resultBoxes.push_back(indices[idx]);
    }

}

bool getRectRatio(cv::Point* rect, double *outMRatio, double *outNRatio) {
    auto lt = rect[0],
         rt = rect[1],
         rb = rect[2],
         lb = rect[3];

    auto diagA = rb - lt;
    auto diagB = rt - lb;

    cv::Mat A(2, 2, cv::DataType<double>::type);
    A.at<double>(0, 0) = diagA.x;
    A.at<double>(1, 0) = diagA.y;
    A.at<double>(0, 1) = diagB.x;
    A.at<double>(1, 1) = diagB.y;

    cv::Mat b(2, 1, cv::DataType<double>::type);

    b.at<double>(0, 0) = rt.x - lt.x;
    b.at<double>(1, 0) = rt.y - lt.y;

    cv::Mat resultMat;
    if (!cv::solve(A, b, resultMat))
        return false;
    double m = resultMat.at<double>(0, 0);
    double n = resultMat.at<double>(1, 0);

    if (m > 0.5)
        *outMRatio = m / (1 - m);
    else
        *outMRatio = (1 - m) / m;
    if (n > 0.5)
        *outNRatio = n / (1 - n);
    else
        *outNRatio = (1 - n) / n;
    return true;
}

bool filterRect(cv::Point *rect) {
    double mratio, nratio;
    if (!getRectRatio(rect, &mratio, &nratio) ||
        mratio > config.maxRectRatio ||
        nratio > config.maxRectRatio) {
        return false;
    }
    return true;
}

int main(int argc, char** argv) {
    config.loadFromArgv(argc, argv);

    if (config.imageFilename == "") {
        config.imageFilename = "/dev/stdin";
    }

    int idx, kdx;
    cv::Mat img = cv::imread(config.imageFilename);

    if (img.data == NULL) {
        cerr << "Cannot read input file \"" << config.imageFilename << "\"" << endl;
        return 1;
    }

    cv::Mat canniedImg;
    config.log("Cannying");
    cv::Canny(img, canniedImg, config.cannyLevel, config.cannyLevel);
    config.log("Done");
        
    if (config.blurSize > 0 || config.kernelSize > 0) {
        config.log("Blurring");
        if (config.blurSize > 0) {
            cv::GaussianBlur(
                canniedImg,
                canniedImg,
                cv::Size(config.blurSize * 2 + 1, config.blurSize * 2 + 1),
                0);
            cv::threshold(canniedImg, canniedImg, 0, 255, cv::THRESH_BINARY);
        }
        if (config.kernelSize > 0) {
            cv::Mat element = cv::getStructuringElement(
                cv::MORPH_ELLIPSE,
                cv::Size(config.kernelSize * 2 + 1, config.kernelSize * 2 + 1),
                cv::Point(config.kernelSize, config.kernelSize));
            cv::dilate(canniedImg, canniedImg, element);
        }
        config.log("Done");
    }

    if (config.dbgCannyFilename != "") {
        cv::imwrite(config.dbgCannyFilename.c_str(), canniedImg);
    }

    cv::Mat hsvImg;
    cv::Mat pinpointImg;
    config.log("Pinpointing");
    cv::cvtColor(img, hsvImg, cv::COLOR_BGR2HSV);
    cv::inRange(hsvImg,
        config.pinpointBegin,
        config.pinpointEnd,
        pinpointImg);
    cv::subtract(pinpointImg, canniedImg, pinpointImg);
    if (config.dbgPinpointFilename != "") {
        cv::imwrite(config.dbgPinpointFilename.c_str(), pinpointImg);
    }

    Filler filler(img, pinpointImg, canniedImg);
    filler.fill();

    bool dbgOut = config.dbgFilename != "";
    if (dbgOut) {
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
    }

    size_t length = filler.resultPoints.size();
    for (idx = 0; idx < length; idx++) {
        if (!filterRect(&filler.resultBoxes[idx * 4])) {
            continue;
        }

        cv::Point pnt = filler.resultPoints[idx];
        cout << "[" << pnt.x << ", " << pnt.y << "]" << endl;

        if (dbgOut)
            cv::circle(img, pnt, 3, cv::Scalar(0, 0, 255), 3);

        for (kdx = 0; kdx < 4; kdx++) {
            cv::Point rectPnt = filler.resultBoxes[idx * 4 + kdx];
            cout << rectPnt.x << " " << rectPnt.y << endl;

            if (dbgOut) {
                cv::line(img,
                    filler.resultBoxes[idx * 4 + kdx],
                    filler.resultBoxes[idx * 4 + (kdx + 1)%4],
                    cv::Scalar(0, 255, 0),
                    3);
            }
        }
        cout << endl;
    }
    if (dbgOut) {
        cv::imwrite(config.dbgFilename, img);
    }
    return 0;
}
