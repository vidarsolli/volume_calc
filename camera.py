import pyrealsense2 as rs
import numpy as np
import time


def threshold(depth_frame, min_depth, max_depth):
    threshold_filter = rs.threshold_filter(min_dist=min_depth, max_dist=max_depth)
    return threshold_filter.process(depth_frame)


def encode_by_colorization(depth_frame, min_depth, max_depth, use_disparity=False):
    """Encoded given realsense depth_frame as colorized image.
    Depth limit are in meters.

    Returns color image as numpy array.

    """
    filtered = threshold(depth_frame, min_depth, max_depth)
    color_filter = rs.colorizer()

    color_filter.set_option(rs.option.histogram_equalization_enabled, 0)
    color_filter.set_option(rs.option.color_scheme, 9.0)
    color_filter.set_option(rs.option.min_distance, min_depth)
    color_filter.set_option(rs.option.max_distance, max_depth)

    if use_disparity:
        filtered = rs.disparity_transform(True).process(filtered)

    colorized = color_filter.process(filtered)
    arr = np.asanyarray(colorized.get_data()).copy()
    return arr


class RealsenseCamera():

    def __init__(self, fps, width, height, roi=None, conv_dist=None):
        self.fps = fps
        self.width = width
        self.height = height
        self.roi = roi
        self.conv_dist = conv_dist
        print(self.conv_dist)

    def grab_raw(self):
        frames = self.pipeline.wait_for_frames()
        fs = self.align.process(frames)
        depth = fs.get_depth_frame()
        color = fs.get_color_frame()
        if not depth or not color:
            return None, None
        depth_img = np.asanyarray(depth.get_data()) / 1000
        color_img = np.asanyarray(color.get_data())

        if self.roi:
            depth_img = depth_img[self.roi[1]:self.roi[3], self.roi[0]:self.roi[2]]
            color_img = color_img[self.roi[1]:self.roi[3], self.roi[0]:self.roi[2]]
        return color_img, depth_img


    def grab(self):
        frames = self.pipeline.wait_for_frames()
        fs = self.align.process(frames)
        depth = fs.get_depth_frame()
        color = fs.get_color_frame()
        if not depth or not color:
            return None, None, None, None

        depth_img = np.asanyarray(depth.get_data()) / 1000
        color_img = np.asanyarray(color.get_data())
        depth_col = encode_by_colorization(depth, 0.1, 1.0, True)
        # Calculate true depth inside the roi
        true_depth = np.zeros((depth_img.shape[0], depth_img.shape[1], 3), dtype=float)
        for r in range(depth_img.shape[0]):
            for c in range(depth_img.shape[1]):
                if depth_img[r, c] == 0.0 and self.conv_dist is not None:
                    true_depth[r, c, :] = 0.0, 0.0, 0.0
                else:
                    d = depth.get_distance(c, r)
                    depth_point = rs.rs2_deproject_pixel_to_point(
                        self.depth_intrin, [c, r], d)
                    true_depth[r,c, :] = depth_point[0], depth_point[1], depth_point[2]
            true_height = true_depth

        if self.roi:
            depth_img = depth_img[self.roi[1]:self.roi[3], self.roi[0]:self.roi[2]]
            color_img = color_img[self.roi[1]:self.roi[3], self.roi[0]:self.roi[2]]
            depth_col = depth_col[self.roi[1]:self.roi[3], self.roi[0]:self.roi[2]]
            true_depth = true_depth[self.roi[1]:self.roi[3], self.roi[0]:self.roi[2], :]
            true_height = true_height[self.roi[1]:self.roi[3], self.roi[0]:self.roi[2], :]
            if self.conv_dist is not None:
                for r in range(true_height.shape[0]):
                    for c in range(true_height.shape[1]):
                        if true_depth[r, c, 2] != 0.0:
                            true_height[r, c, 2] = self.conv_dist[r, c] - true_depth[r, c, 2]

        return color_img, depth_img, depth_col, true_height


    def start(self):
        self.pipeline = rs.pipeline()
        align_to = rs.stream.color
        self.align = rs.align(align_to)

        cfg = rs.config()
        cfg.enable_stream(
            rs.stream.depth,
            self.width,
            self.height,
            rs.format.z16,
            self.fps,
        )
        cfg.enable_stream(
            rs.stream.color,
            self.width,
            self.height,
            rs.format.bgr8,
            self.fps,
        )
        self.pipeline.start(cfg)
        # Retreive the first image and get internal references
        frames = self.pipeline.wait_for_frames()
        fs = self.align.process(frames)
        depth = fs.get_depth_frame()
        color = fs.get_color_frame()

        self.dprofile = depth.get_profile()
        print("Dprofile: ", self.dprofile)
        self.cprofile = color.get_profile()
        print("Cprofile: ", self.cprofile)

        self.cvsprofile = rs.video_stream_profile(self.cprofile)
        print("Cvsprofile: ", self.cvsprofile)
        self.dvsprofile = rs.video_stream_profile(self.dprofile)
        print("Dvsprofile: ", self.dvsprofile)

        self.color_intrin = self.cvsprofile.get_intrinsics()
        print("Color intrinsics: ", self.color_intrin)
        self.depth_intrin = self.dvsprofile.get_intrinsics()
        print("Depth intrinsics: ", self.depth_intrin)
        self.extrin = self.dprofile.get_extrinsics_to(self.cprofile)
        print("Extrinsics: ", self.extrin)

    def stop(self):
        self.pipeline.stop()

