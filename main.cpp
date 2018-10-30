/*
Make annotations by hand:
	./annotations -i <inputdir> outfile

*/

#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <boost/filesystem.hpp>
#include <opencv2/opencv.hpp>

namespace fs = boost::filesystem;
const int CIRCLE_RADIUS = 3;
typedef std::vector<std::vector<cv::Point>> AnnoType;
typedef std::vector<std::array<cv::Point, 2>> RectType;

void next_image ();
void next_person ();
void next_keypoint (cv::Point);
void prev_image ();
void prev_person ();
void prev_keypoint ();
void inc_lbl_cur();
void load_image_filenames_and_bbs (std::string& images_list_file);

std::deque<fs::path> images;
std::deque<std::vector<int>> bbs;

cv::Mat img;
AnnoType annotations;
std::vector<cv::Point> dummyAnnotation;
std::vector<cv::Point>& annotation = dummyAnnotation;
int current_index; /* index of image */
RectType bndboxes; /* bounding boxes for current image */
int person_index;
cv::Point dummypos(0, 0);

using namespace std;

const int lbl_n = 20; // actually the index of the last item in the list
int lbl_cur;
const char *lbls[] = {
	"Nose",
	"LEye",
	"REye",
	"LEar",
	"REar",
    "Head",
    "Neck",
	"LShoulder",
	"RShoulder",
	"LElbow",
	"RElbow",
	"LWrist",
	"RWrist",
    "Thrx",
	"LHip",
	"RHip",
    "Pelv",
	"LKnee",
	"Rknee",
	"LAnkle",
	"RAnkle",
};

/* Output some info about current state */
void dbg() {
	cout << endl << "imrem " << images.size()-1-current_index << " p " << person_index+1 << ": " << setw(2) << lbl_cur << "/" << lbl_n << " " << lbls[lbl_cur] << " ";
	cout.flush();
}

void annotating(int event, int x, int y, int flags, void *params){
	if(event != cv::EVENT_LBUTTONUP) return;

	std::cout << "(x, y) = (" << x << ", " << y << ")";
	cv::Point pos(x, y);
	next_keypoint(pos);
}

void load_annotation(const std::string& inputfile, AnnoType& annotations){
	std::ifstream ifs(inputfile);
	if(! ifs){
		std::cerr << "Input file is incorrect" << std::endl;
		exit(EXIT_FAILURE);
	}
	std::string line;
	while(getline(ifs, line)){
		lbl_cur = 0;
		std::istringstream iss(line);
		std::string token;
		std::vector<cv::Point> anno;
		while(getline(iss, token, ',')){
			cv::Point pos;
			pos.x = std::stoi(token);
			getline(iss, token, ',');
			pos.y = std::stoi(token);
			lbl_cur ++;
			anno.push_back(pos);
		}
		annotations.push_back(anno);
	}
}

void save_annotation(const AnnoType& annotations, const std::string& outputfile){
	std::ofstream ofs(outputfile);
	for(auto &annotation: annotations){
		if (annotation.size() != 0)
			ofs << images[0].string() << endl;
		images.pop_front();
		if(annotation.size() != 0) ofs << annotation[0].x << "," << annotation[0].y;
		for(int i=1; i<annotation.size(); i++){
			ofs << "," << annotation[i].x << "," << annotation[i].y;
		}
		if (annotation.size() != 0)
			ofs << std::endl;
	}
}

int main(int argc, char **argv){
	if(argc < 3){
		std::cerr << "usage: " << argv[0] << " images_and_bbs_list outputfile" << std::endl;
		return EXIT_FAILURE;
	}

	std::string images_list_file, outputfile, inputfile="";
	if(argc == 3){
		images_list_file = argv[1];
		outputfile = argv[2];
	}else if(argc == 4){
		images_list_file = argv[1];
		inputfile = argv[2];
		outputfile = argv[3];
	}

	load_image_filenames_and_bbs(images_list_file);

	if(images.size() == 0){
		std::cerr << "No images are found" << std::endl;
		return EXIT_FAILURE;
	}

	if(inputfile==""){
		annotations.resize(images.size(), std::vector<cv::Point>(0));
	}else{
		load_annotation(inputfile, annotations);
	}
	cv::namedWindow("image", 0);

	int prev_index = -1;
	int key = 0;
	bool is_loop = true;
	cv::setMouseCallback("image", annotating);
	while(is_loop){
		if(current_index != prev_index){
			/* Load image from file */
			auto p = images[current_index];
			img = cv::imread(p.string());
			if(img.empty()){
				std::cerr << "loading " << p.string() << " failed" << std::endl;
				return EXIT_FAILURE;
			}
			std::cout << "LOADING FILE " << p.string() << endl;
			prev_index = current_index;
			dbg();
			/* Prep bounding boxes */
			bndboxes.clear();
			auto curbbs = bbs[current_index];
			for (int i = 0; i < curbbs.size(); i += 4) {
				bndboxes.push_back( { cv::Point(curbbs[i], curbbs[i+1]),
					cv::Point(curbbs[i+2], curbbs[i+3]) } );
			}
		}

		/* Draw bounding box */
		{
			auto pt1 = cv::Point(
				bbs[current_index][4*person_index+0],
				bbs[current_index][4*person_index+1]);
			auto pt2 = cv::Point(
				bbs[current_index][4*person_index+2],
				bbs[current_index][4*person_index+3]);
			auto color = cv::Scalar(50, 255, 25);
			cv::rectangle(img, pt1, pt2, color);
		}

		/* Draw annotation dot */
		annotation = annotations[current_index];
		for(int i=0; i<annotation.size(); i++){
			auto color = cv::Scalar(i*255/annotation.size(), 0, 255);
			cv::circle(img, annotation[i], CIRCLE_RADIUS, color, -1);
		}


		cv::imshow("image", img);
		key = cv::waitKey(100);

		switch(key){
			case 'j':
			case 'f':
			case ' ':
			case 83: /* next image */
				current_index = std::min<int>(++current_index, images.size()-1);
				person_index = 0;
				dbg();
				break;
			case 'k':
			case 'b':
			case 81: /* previous image */
				current_index = std::max<int>(0, --current_index);
				dbg();
				break;
			case 's': /* skip keypoint */
				next_keypoint(dummypos); break;
			case 8: /* (backspace) remove keypoint */
				prev_keypoint(); break;
			case 'q':
			case 27:
				is_loop = false;
				break;
		}
	}

	save_annotation(annotations, outputfile);
	return EXIT_SUCCESS;
}

void next_person () {
	person_index ++;
}
void prev_person () {
	person_index --;
}
void next_keypoint (cv::Point pos) {
	annotations[current_index].push_back(pos);
	inc_lbl_cur();
}
void prev_keypoint () {
	if(annotation.size()>0){
		annotation.pop_back();
		img = cv::imread(images[current_index].string());
		lbl_cur --;
		if (lbl_cur < 0) {
			if (person_index) {
				prev_person();
				lbl_cur = lbl_n;
			} else {
				lbl_cur = 0;
			}
		}
	}
	dbg();
}
/* Increment the cursor which says which keypoint is currently being annotated */
void inc_lbl_cur() {
	lbl_cur ++;
	if (lbl_cur > lbl_n) {
		std::cout << "END of keypoints" << endl;
		lbl_cur = 0;
		next_person();
	}
	dbg();
}

void load_image_filenames_and_bbs (string& images_list_file) {
	ifstream inFile(images_list_file, ios::in);
	string line;
	if ( inFile.is_open() ) {
		while ( getline(inFile, line) ) {
			if (line.length() == 0) continue;
			vector<int> bbs_for_img;
			int s = 0, e = line.find("\t");
			if (e == string::npos) e = line.length();
			images.push_back(line.substr(s, e - s));
			for (s = e + 1; s < line.length(); s = e + 1) {
				e = line.find("\t", s);
				cout << "e " << e << ' ';
				if (e == string::npos) e = line.length();
				cout << "substr " << s << " " << e << ' ' << line.length() << ' ' <<line.substr(s, e - s) << endl;
				bbs_for_img.push_back(std::stoi(line.substr(s, e - s)));
			}
			assert(bbs_for_img.size());
			assert(bbs_for_img.size() % 4 == 0);
			bbs.push_back(bbs_for_img);
		}
	}
}