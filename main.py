import numpy as np
import getopt
import sys
import os
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
import threading
import queue
from socket_com import send_json, send_file

json_queue = queue.Queue()

json_msg = {
    "image_name": "image.jpg",
    "time_since_detection": 0.0,
    "width": 0.0,
    "length": 0.0,
    "height": 0.0
}


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

conv_dist = np.load("conveyor_surface.npy")
check_surface = np.load("check_surface.npy")

print("OpenCV version: ", cv2.__version__)
height = cp["image_height"]
width = cp["image_width"]
fps = cp["fps"]
camera = RealsenseCamera(fps, width, height, cp["roi"][0], conv_dist)
camera.start()

# Start the socket communication threads

thr1 = threading.Thread(target=send_file, args=("127.0.0.1", 65120, cp["image_directory"]))
thr1.start()
thr2 = threading.Thread(target=send_json, args=("127.0.0.1", 65110, json_queue))
thr2.start()


cap = cv2.VideoCapture(0)

for idx, process in enumerate(cp["process_chain"]):
    cv2.namedWindow(str(idx)+"-"+process, cv2.WINDOW_NORMAL)

while True:
    # Update process parameters if an Update messaage is received
    if check_message() == "UPDATE":
        process_chain = cp["process_chain"]
        with open("config.json") as file:
            cp = json.load(file)
        if process_chain != cp["process_chain"]:
            cv2.destroyAllWindows()
            for idx, process in enumerate(cp["process_chain"]):
                cv2.namedWindow(str(idx) + "-" + process, cv2.WINDOW_NORMAL)

    # Wait for an object
    color_img, depth_img, depth_col, box_pos, box_dim, detection_time = process_image(camera, cp, check_surface, True)

    # Grab image from overview camera and save the file
    filename = datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f") + ".jpg"
    ret, overview_image = cap.read()
    if ret:
        cv2.imwrite(os.path.join(cp["image_directory"], filename), overview_image)

    # Send data to user
    json_msg["image_name"] = filename
    json_msg["time_since_detection"] = time.time() - detection_time
    json_msg["length"] = box_dim[0]*1000
    json_msg["width"] = box_dim[1]*1000
    json_msg["height"] = box_dim[2]*1000
    json_queue.put(json_msg)

    if cp["save_images"] == "True":
        file_name = datetime.now().strftime("%Y-%m-%d-%H-%M-%S-%f")
        cv2.imwrite("data/" + file_name + "_depth.jpg", depth_col)
        cv2.imwrite("data/" + file_name + "_color.jpg", color_img)
    cv2.rectangle(depth_col, (cp["roi"][1][0]-cp["roi"][0][0], cp["roi"][1][1]-cp["roi"][0][1]),
                  (cp["roi"][1][2]-cp["roi"][0][0], cp["roi"][1][3]-cp["roi"][0][1]), (0, 255, 0), 2)
    if len(box_pos) > 0:
        cv2.drawContours(color_img, [box_pos], 0, (255, 0, 0), 2)
    font = cv2.FONT_HERSHEY_SIMPLEX

    if len(box_dim) > 0:
        l_text = "Length: " + str(int(box_dim[0]*1000)) + " mm"
        w_text = "Width: " + str(int(box_dim[1]*1000)) + " mm"
        h_text = "Height: " + str(int(box_dim[2]*1000)) + " mm"
        cv2.putText(color_img, l_text, (10, 30), font, 0.5, (255, 255, 255), 1)
        cv2.putText(color_img, w_text, (10, 60), font, 0.5, (255, 255, 255), 1)
        cv2.putText(color_img, h_text, (10, 90), font, 0.5, (255, 255, 255), 1)

    cv2.imshow("depth", depth_col)
    cv2.imshow("color", color_img)
    cv2.imshow("Overview camera", overview_image)


    cv2.waitKey(1)


