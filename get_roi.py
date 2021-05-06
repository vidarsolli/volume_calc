# import the necessary packages
import cv2 as cv
import time
import json
import sys, getopt
from camera import RealsenseCamera
import numpy as np


# initialize the list of reference points and boolean indicating
# whether cropping is being performed or not
refPt = []
cropping = False
no_of_rois = 0
MAX_ROIS = 4


def click_and_crop(event, x, y, flags, param):
    # grab references to the global variables
    global refPt, cropping, no_of_rois

    # if the left mouse button was clicked, record the starting
    # (x, y) coordinates and indicate that cropping is being
    # performed
    if event == cv.EVENT_LBUTTONDOWN:
        if len(refPt) >= 2:
            refPt.append((x, y))
        else:
            refPt = [(x, y)]
        cropping = True

    # check to see if the left mouse button was released
    elif event == cv.EVENT_LBUTTONUP:
        # record the ending (x, y) coordinates and indicate that
        # the cropping operation is finished
        refPt.append((x, y))
        cropping = False

        # draw a rectangle around the region of interest
        cv.rectangle(image, refPt[no_of_rois*2], refPt[no_of_rois*2+1], (0, 255, 0), 2)
        cv.imshow("image", image)
        no_of_rois += 1


print("Usage: python3 read_roi.py")
print("Press and hold the left mouse button and drag the cursor ")
print("to cover the ROI. Release the left mouse button when finished.")
print("Commands:")
print("r:  restart the process.")
print("c:  Complete and store the ROIs in the config.json file.")
print("n:  Restart the process and take a new picture")

# Get the input json file
config_file = "config.json"
try:
    myOpts, args = getopt.getopt(sys.argv[1:], "i:")
except getopt.GetoptError as e:
    print(str(e))
    print("Usage: %s -i <json_file>" % sys.argv[0])
    sys.exit(2)

for o, a in myOpts:
    if o == '-i':
        config_file = a

# Ooen the config file
with open(config_file) as file:
    cp = json.load(file)

camera = RealsenseCamera(cp["fps"], cp["image_width"], cp["image_height"])
camera.start()
image, depth_img, _, _ = camera.grab()
clone = image.copy()
cv.namedWindow("image")
cv.setMouseCallback("image", click_and_crop)

# keep looping until the 'q' key is pressed
while True:

    # display the image and wait for a keypress
    cv.circle(image, (int(image.shape[1] / 2), int(image.shape[0] / 2)), 2, (0, 0, 255), -1)
    cv.circle(image, (int(image.shape[1] / 2) + cp["xp_dist"], int(image.shape[0] / 2)), 2, (0, 0, 255), -1)
    cv.circle(image, (int(image.shape[1] / 2), int(image.shape[0] / 2) + cp["yp_dist"]), 2, (0, 0, 255), -1)
    cv.circle(image, (int(image.shape[1] / 2) - cp["xp_dist"], int(image.shape[0] / 2)), 2, (0, 0, 255), -1)
    cv.circle(image, (int(image.shape[1] / 2), int(image.shape[0] / 2) - cp["yp_dist"]), 2, (0, 0, 255), -1)

    cv.imshow("image", image)
    key = cv.waitKey(1) & 0xFF

    # if the 'r' key is pressed, reset the cropping region
    if key == ord("r"):
        image = clone.copy()
        no_of_rois = 0
        refPt = ()

    # if the 'c' key is pressed, break from the loop
    elif key == ord("c"):
        break

    # if the 'n' key is pressed, capture a new image and clear rois
    if key == ord("n"):
        image, _, _, _ = camera.grab()
        no_of_rois = 0
        refPt = ()


# if there are two reference points, then crop the region of interest
# from the image and display it
if len(refPt) >= 2:
    cp["roi"] = list()
    print("Number og rectangles: ", no_of_rois)
    print(refPt)
    for i in range(min(int(len(refPt)/2), MAX_ROIS)):
        #roi = clone[refPt[i*2][1]:refPt[i*2+1][1], refPt[i*2][0]:refPt[i*2+1][0]]
        #cv.imshow("ROI", roi)
        cp["roi"].append((refPt[i*2][0], refPt[i*2][1], refPt[i*2+1][0], refPt[i*2+1][1]))
    with open('config.json', 'w') as f:
        json.dump(cp, f, indent=4)
    #cv.waitKey(0)


# close all open windows
cv.destroyAllWindows()

print("Calculate distance to conveyor surface")
roi = cp["roi"][0]
conveyor_surface = np.zeros((cp["image_height"], cp["image_width"]), dtype=float)
# Calculate average z-distance
_, _, _, surface = camera.grab()
n = 0
average = 0.0
conveyor_surface = conveyor_surface[roi[1]:roi[3], roi[0]:roi[2]]
surface = surface[roi[1]:roi[3], roi[0]:roi[2]]
print("Surface: ", np.max(surface), np.min(surface))
for r in range(surface.shape[0]):
    for c in range(surface.shape[1]):
        if surface[r,c] != 0.0:
            n += 1
            average += surface[r,c]
average = average/n
print("Average depth: ", average)
for r in range(surface.shape[0]):
    for c in range(surface.shape[1]):
        conveyor_surface[r, c] = average

np.save("conveyor_surface.npy", conveyor_surface)

cp["image_width"], cp["image_height"]