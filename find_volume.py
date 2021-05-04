import camera
import numpy as np
import pyrealsense2 as rs
import time
import matplotlib.pyplot as plt
import cv2
import json
import zmq
import math
from camera import RealsenseCamera

def apply_colormap(depth, max_dist=5.0):
    return cv2.applyColorMap(
        cv2.convertScaleAbs(depth, alpha=255 / max_dist), cv2.COLORMAP_JET
    )
def angle_cos(p0, p1, p2):
    d1, d2 = (p0-p1).astype('float'), (p2-p1).astype('float')
    return abs( np.dot(d1, d2) / np.sqrt( np.dot(d1, d1)*np.dot(d2, d2) ) )

def process_image(camera, cp, show_image):
    object_found = False
    while not object_found:
        color_img, depth_img, depth_col = camera.grab()
        # Check if object on conveyor. ROI[1] is the check area
        check_img = depth_img[cp["roi"][1][1]:cp["roi"][1][3], cp["roi"][1][0]:cp["roi"][1][2]]
        height = cp["max_depth"] - check_img
        height_sum = np.sum(height)
        height_avr = height_sum/(check_img.shape[0]*check_img.shape[1])
        if height_avr > cp["trigger_height"]:
            object_found = True
    print("Object detected, average height: ", height_avr)
    color_img = color_img[cp["roi"][0][1]:cp["roi"][0][3], cp["roi"][0][0]:cp["roi"][0][2]]
    depth_img = depth_img[cp["roi"][0][1]:cp["roi"][0][3], cp["roi"][0][0]:cp["roi"][0][2]]
    depth_col = depth_col[cp["roi"][0][1]:cp["roi"][0][3], cp["roi"][0][0]:cp["roi"][0][2]]

    """
    original_img = color_img.copy()
    i = 0
    color_img = color_img[cp["roi"][i][1]:cp["roi"][i][3], cp["roi"][i][0]:cp["roi"][i][2]]
    depth_img = depth_img[cp["roi"][i][1]:cp["roi"][i][3], cp["roi"][i][0]:cp["roi"][i][2]]
    # cv2.imshow("Temp1",color_img)

    # remove ground and things above max height
    new_height = np.abs(cp["roi"][i][1] - cp["roi"][i][3])
    new_width = np.abs(cp["roi"][i][0] - cp["roi"][i][2])
    depth = apply_colormap(depth_img)
    # cv2.imshow("Temp2",depth)
    if cp["depth_filter"] == "True":
        for h in range(new_height):
            for w in range(new_width):
                if depth_img[h, w] > cp["max_depth"] or depth_img[h, w] < cp["min_depth"] or depth_img[h, w] == 0:
                    color_img[h, w, :] = (0, 0, 0)

    img = color_img.copy()
    contour = None
    box = None
    cx = 0
    cy = 0
    dist = 0
    angr = 0.0
    for idx, process in enumerate(cp["process_chain"]):
        if process == "configure":
            cv2.circle(original_img, (int(original_img.shape[1] / 2), int(original_img.shape[0] / 2)), 2, (0, 0, 255), -1)
            cv2.circle(original_img, (int(original_img.shape[1] / 2) + cp["xp_dist"], int(original_img.shape[0] / 2)), 2, (0, 0, 255), -1)
            cv2.circle(original_img, (int(original_img.shape[1] / 2), int(original_img.shape[0] / 2) + cp["yp_dist"]), 2, (0, 0, 255), -1)
            cv2.circle(original_img, (int(original_img.shape[1] / 2) - cp["xp_dist"], int(original_img.shape[0] / 2)), 2, (0, 0, 255), -1)
            cv2.circle(original_img, (int(original_img.shape[1] / 2), int(original_img.shape[0] / 2) - cp["yp_dist"]), 2, (0, 0, 255), -1)
            img = original_img
        if process == "cvtColor":
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if process == "GaussianBlur":
            img = cv2.GaussianBlur(img, (cp["blur_kernel_size"], cp["blur_kernel_size"]), 0)
        if process == "Canny":
            img = cv2.Canny(img, cp["canny_thresh1"], cp["canny_thresh2"])
        if process == "dilate":
            img = cv2.dilate(img, None)
        if process == "threshold":
            ret, img = cv2.threshold(img, cp["threshold_thresh"], cp["threshold_max"], cv2.THRESH_BINARY)
        if process == "adaptiveThreshold":
            img = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, \
                                        cv2.THRESH_BINARY, 11, 2)
        if process == "findContours":
            if len(img.shape) == 3:
                img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            else:
                img_gray = img.copy()
            _, contours, hierarchy = cv2.findContours(img_gray, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            # Find longes contour
            cont_idx = -1
            for i, cont in enumerate(contours):
                if cv2.contourArea(cont) > cp["box_min_area"]:
                    cont_idx = i
            if cont_idx != -1:
                contour = contours[cont_idx]
                pts = np.array(contour, dtype=np.int32)
                img = cv2.polylines(img, [pts], True, (127, 127, 127), 1)
        if process == "boundingRect":
            if contour is not None:
                img = np.zeros((img.shape[0], img.shape[1], 3), np.uint8)
                if cp["bounding_rect_best_fit"] == "True":
                    rect = cv2.minAreaRect(contour)
                    box = cv2.boxPoints(rect)
                    box = np.int0(box)
                    cv2.drawContours(img, [box], 0, (255, 0, 0), 2)
                else:
                    x, y, w, h = cv2.boundingRect(contour)
                    cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    box[0] = (x, y)
                    box[1] = (x + w, y)
                    box[2] = (x + w, y + h)
                    box[3] = (x, y + h)
                box_found = True
            else:
                print("boundingRect, No contour avalable")

        if process == "HoughLines":
            # This returns an array of r and theta values
            imga = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            imga = cv2.Canny(imga, cp["canny_thresh1"], cp["canny_thresh2"])
            pix_accuracy = cp["hough_pix_accuracy"]
            ang_accuracy = cp["hough_ang_accuracy"]
            min_length = cp["hough_min_length"]
            lines = cv2.HoughLines(imga, pix_accuracy, ang_accuracy * np.pi / 180, min_length)
            # The below for loop runs till r and theta values
            # are in the range of the 2d array
            if lines is not None:
                for r, theta in lines[0]:
                    # Stores the value of cos(theta) in a
                    a = np.cos(theta)

                    # Stores the value of sin(theta) in b
                    b = np.sin(theta)

                    # x0 stores the value rcos(theta)
                    x0 = a * r

                    # y0 stores the value rsin(theta)
                    y0 = b * r

                    # x1 stores the rounded off value of (rcos(theta)-1000sin(theta))
                    x1 = int(x0 + 1000 * (-b))

                    # y1 stores the rounded off value of (rsin(theta)+1000cos(theta))
                    y1 = int(y0 + 1000 * (a))

                    # x2 stores the rounded off value of (rcos(theta)+1000sin(theta))
                    x2 = int(x0 - 1000 * (-b))

                    # y2 stores the rounded off value of (rsin(theta)-1000cos(theta))
                    y2 = int(y0 - 1000 * (a))

                    # cv2.line draws a line in img from the point(x1,y1) to (x2,y2).
                    # (0,0,255) denotes the colour of the line to be
                    # drawn. In this case, it is red.
                    img = cv2.line(img, (x1, y1), (x2, y2), (200, 50, 100), 2)
        if process == "Properties":
            if contour is not None:
                M = cv2.moments(contour)
                ang = 0.0
                if M['m00'] != 0:
                    cx = int(M['m10'] / M['m00'])
                    cy = int(M['m01'] / M['m00'])
                rect = cv2.minAreaRect(contour)
                (x, y), (width, height), ang = rect
                if width < height:
                    ang = ang - 90
                #print("Rect: ", rect, ang)
                angr = ang * math.pi / 180.0
                cv2.circle(img, (cx, cy), 7, (0, 0, 255), -1)
                cv2.line(img, (cx, cy), (int(cx + 100 * math.cos(angr)), int(cy + 100 * math.sin(angr))), (0, 200, 200), 2)
                # Find distance to object
                obj_dist = 0.0
                n = 0
                for x in range(11):
                    for y in range(11):
                        if depth_img[cy + y, cx + x] != 0:
                            n += 1
                            obj_dist += depth_img[cy + y, cx + x]
                if n > 0.0:
                    dist = obj_dist / n
                else:
                    dist = 0.0

                # if np.sqrt(np.square(box[0][0]+np.square(box[1][0]))) > np.sqrt(np.square(box[0][0] + np.square(box[1][0])))
            else:
                print("Properties, no contour available")
        if show_image:
            cv2.imshow(str(idx) + "-" + process, img)
            cv2.waitKey(1)
    """
    return color_img, depth_img, depth_col
