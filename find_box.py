import numpy as np
import getopt
import sys
import pyrealsense2 as rs
import time
import matplotlib.pyplot as plt
import cv2
import json
import zmq
import math
from camera import RealsenseCamera
from find_volume import process_image
import time
from datetime import datetime




def apply_colormap(depth, max_dist=5.0):
    return cv2.applyColorMap(
        cv2.convertScaleAbs(depth, alpha=255 / max_dist), cv2.COLORMAP_JET
    )
def angle_cos(p0, p1, p2):
    d1, d2 = (p0-p1).astype('float'), (p2-p1).astype('float')
    return abs( np.dot(d1, d2) / np.sqrt( np.dot(d1, d1)*np.dot(d2, d2) ) )

def check_message():
    msg = None
    try:
        msg = sock.recv_pyobj(zmq.NOBLOCK)
    except:
        return msg
    print("Message received, ", msg)
    return msg

try:
    myOpts, args = getopt.getopt(sys.argv[1:], "i:")
except getopt.GetoptError as e:
    print(str(e))
    print("Usage: %s -i <path to base config file>" % sys.argv[0])
    sys.exit(2)
config_file = "config.json"
for o, a in myOpts:
    if o == '-i':
        config_file = a

print("Selected config file: ",config_file )

# Ooen the config file
with open(config_file) as file:
    cp = json.load(file)

sock = zmq.Context().socket(zmq.SUB)
sock.setsockopt_string(zmq.SUBSCRIBE, "")
#data_sock.setsockopt(zmq.CONFLATE, 1)
sock.connect("tcp://localhost:60001")


print("OpenCV version: ", cv2.__version__)
height = cp["image_height"]
width = cp["image_width"]
fps = cp["fps"]
camera = RealsenseCamera(fps, width, height)
camera.start()

for idx, process in enumerate(cp["process_chain"]):
    cv2.namedWindow(str(idx)+"-"+process, cv2.WINDOW_NORMAL)

while True:
    # Update process parameters if Update messaage is received
    if check_message() == "UPDATE":
        process_chain = cp["process_chain"]
        with open("config.json") as file:
            cp = json.load(file)
        if process_chain != cp["process_chain"]:
            cv2.destroyAllWindows()
            for idx, process in enumerate(cp["process_chain"]):
                cv2.namedWindow(str(idx) + "-" + process, cv2.WINDOW_NORMAL)

    color_img, depth_img, depth_col = process_image(camera, cp, True)
    cv2.imshow("depth", depth_col)
    cv2.imshow("color", color_img)
    cv2.waitKey(1)
    if cp["save_images"] == "True":
        file_name = datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")
        cv2.imwrite("data/" + file_name + "_depth.jpg", depth_col)
        cv2.imwrite("data/" + file_name + "_color.jpg", color_img)
    time.sleep(2)

