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

def process_image(camera, cp, check_surface, show_image):
    # Check the ROI[1] area for objects.
    # An object is detected if 10% of the pixels in the ROI[1] area are
    # greater than "trigger_height".
    object_found = False
    chk_roi = (cp["roi"][1][0]-cp["roi"][0][0], cp["roi"][1][1]-cp["roi"][0][1],
                       cp["roi"][1][2] - cp["roi"][0][0], cp["roi"][1][3] - cp["roi"][0][1])
    while not object_found:
        color_img, depth_img = camera.grab_raw()
        check_img = depth_img[chk_roi[1]:chk_roi[3], chk_roi[0]:chk_roi[2]]
        trigged_count = np.sum((check_surface - check_img) > cp["trigger_height"])
        object_found = trigged_count > int(check_img.shape[0]*check_img.shape[1]*0.1)
    print("Object detected, trigged cound: ", trigged_count, np.max(check_img), np.min(check_img))

    # Get true height ( relative to the conveyor belt) of the object
    color_img, depth_img, depth_col, height = camera.grab()

    # remove ground and find average height of object
    avr_height = 0
    n = 0
    if cp["depth_filter"] == "True":
        for r in range(height.shape[0]):
            for c in range(height.shape[1]):
                if height[r, c, 2] < cp["min_height"] or height[r, c, 2] == 0:
                    color_img[r, c, :] = (0, 0, 0)
                else:
                    avr_height += height[r, c, 2]
                    n += 1
    if n > 0:
        avr_height = avr_height/n

    img = color_img.copy()
    contour = None
    box = []
    cx = 0
    cy = 0
    dist = 0
    angr = 0.0
    for idx, process in enumerate(cp["process_chain"]):
        # Convert color image to gray scale
        if process == "cvtColor":
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Make the image blurry
        if process == "GaussianBlur":
            img = cv2.GaussianBlur(img, (cp["blur_kernel_size"], cp["blur_kernel_size"]), 0)
        if process == "Canny":
            img = cv2.Canny(img, cp["canny_thresh1"], cp["canny_thresh2"])
        if process == "dilate":
            img = cv2.dilate(img, None)
        #
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
            # Find longest contour
            cont_idx = -1
            # Select the contour with the largest area
            max_area = 0.0
            for i, cont in enumerate(contours):
                area = cv2.contourArea(cont)
                if area > max_area:
                    cont_idx = i
                    max_area = area
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
                    box.append([x, y])
                    box.append([x + w, y])
                    box.append([x + w, y + h])
                    box.append([x, y + h])
                    box = np.asarray(box)
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
                print(box)
                box_pos = []
                box_pos.append([height[box[0][0],box[0][1],0], height[box[0][0],box[0][1],1]])
                box_pos.append([height[box[1][0],box[1][1],0], height[box[1][0],box[1][1],1]])
                box_pos.append([height[box[2][0],box[2][1],0], height[box[2][0],box[2][1],1]])
                box_pos.append([height[box[3][0],box[3][1],0], height[box[3][0],box[3][1],1]])
                print("Box pos: ", box_pos)
                print("dimention: ", width, height, avr_height)
                """
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
                """
            else:
                print("Properties, no contour available")
        if show_image:
            cv2.imshow(str(idx) + "-" + process, img)
            cv2.waitKey(1)



    #Calculate box properties
    print("Calcutating final properties")
    print("Box coordinates: ", box)
    print("Height dim: ", height.shape)
    # Check if box dimensions are outside height area
    for i in range(4):
        if box[i][0] >= height.shape[1]:
            box[i][0] = height.shape[1] - 1
            print("Correcting box pos[0]")
        if box[i][1] >= height.shape[0]:
            box[i][1] = height.shape[0] - 1
            print("Correcting box pos[1]")
    box_dim = []
    box_pos = []
    if contour is not None:
        M = cv2.moments(contour)
        ang = 0.0
        if M['m00'] != 0:
            cx = int(M['m10'] / M['m00'])
            cy = int(M['m01'] / M['m00'])
        rect = cv2.minAreaRect(contour)
        (x, y), (rect_width, rect_height), ang = rect
        box_pos.append([height[box[0][1], box[0][0], 0], height[box[0][1], box[0][0], 1]])
        box_pos.append([height[box[1][1], box[1][0], 0], height[box[1][1], box[1][0], 1]])
        box_pos.append([height[box[2][1], box[2][0], 0], height[box[2][1], box[2][0], 1]])
        box_pos.append([height[box[3][1], box[3][0], 0], height[box[3][1], box[3][0], 1]])
        rect_width = np.sqrt(abs(box_pos[0][0]-box_pos[1][0]) * abs(box_pos[0][0]-box_pos[1][0])
                             + abs(box_pos[0][1]-box_pos[1][1]) * abs(box_pos[0][1]-box_pos[1][1]))
        rect_length = np.sqrt(abs(box_pos[1][0]-box_pos[2][0]) * abs(box_pos[1][0]-box_pos[2][0])
                             + abs(box_pos[1][1]-box_pos[2][1]) * abs(box_pos[1][1]-box_pos[2][1]))
        box_dim = [rect_width, rect_length, avr_height]

        print("Box pos: ", box_pos)
        print("Box: ", box)
        print("dimention: ", rect_width, rect_length, avr_height)


    return color_img, depth_img, depth_col, box, box_dim
