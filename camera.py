import pyrealsense2 as rs
import numpy as np


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

    def __init__(self, fps, width, height):
        self.fps = fps
        self.width = width
        self.height = height

    def grab(self):
        frames = self.pipeline.wait_for_frames()
        fs = self.align.process(frames)
        depth = fs.get_depth_frame()
        color = fs.get_color_frame()
        if not depth or not color:
            return None, None

        depth_img = np.asanyarray(depth.get_data()) / 1000
        color_img = np.asanyarray(color.get_data())
        depth_col = encode_by_colorization(depth, 0.1, 1.0, True)

        return color_img, depth_img, depth_col

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

    def stop(self):
        self.pipeline.stop()