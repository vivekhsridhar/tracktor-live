# Pranav Minasandra, Vivek H Sridhar, and Isaac Planas-Sitja
# 15 Apr 2025
# pminasandra.github.io

"""
suite of helper functions to aid in tracking objects in video
"""

import os.path
from os.path import join as joinpath

import cv2
import numpy as np

from . import tracktor as tr

class VideoEndedError(IOError):
    """Raised when a video has reached its end."""
    def __init__(self, message="The video has ended."):
        super().__init__(message)

def get_vid(source):
    """
    Gets a cv2.VideoCapture object from given source
    Args:
        source (int or str): filename or camera device number
    Returns:
        cv2.VideoCapture object
    """

    vidtype = "cam" if isinstance(source, int) else "file"
    cap = cv2.VideoCapture(source)
    assert cap.isOpened(), f"could not access source {vidtype}: {source}."

    return cap

def get_frame(cap):
    """
    gets one frame from cap
    Args:
        cap (cv2.VideoCapture)
    Returns:
        frame, frame_index
    """

    assert cap.isOpened()
    ret, frame = cap.read()
    if not ret:
        raise VideoEndedError("frame could not be obtained")
    frame_index = cap.get(cv2.CAP_PROP_POS_FRAMES)

    return frame, frame_index


def get_contours(frame, block_size,
                 meas_last, meas_now,
                 min_area, max_area,
                 offset, scaling,
                 fps=None,
                 invert=True,
                 draw_contours=False):
    """
    Processes a video frame to detect object contours using thresholding and contour detection.

    Args:
        frame (np.ndarray): The current video frame.
        block_size (int): Size of the neighborhood for adaptive thresholding. Must be odd.
        meas_last (list): List of (x, y) coordinates from the previous frame.
        meas_now (list): List of (x, y) coordinates detected in the current frame (to be updated).
        min_area (int): Minimum area for a contour to be considered valid.
        max_area (int): Maximum area for a contour to be considered valid.
        offset (int): Offset value subtracted during adaptive thresholding.
        scaling (float): Scale factor for resizing the input frame.
        fps (float, optional): Frames per second, unused here but included for compatibility.
        invert (bool, default=True): Whether to invert the thresholded image.
        draw_contours (bool, default=False): Whether to draw detected contours on the frame.

    Returns:
        processed frame, list of contours, updated meas_last, updated meas_now
    """

    del fps
    frame = cv2.resize(frame,
                            None,
                            fx=scaling,
                            fy=scaling,
                            interpolation=cv2.INTER_LINEAR
                        )
    thresh = tr.colour_to_thresh(frame, block_size, offset, invert=invert)
    final, contours, meas_last, meas_now = tr.detect_and_draw_contours(
                                            frame,
                                            thresh,
                                            meas_last=meas_last,
                                            meas_now=meas_now,
                                            min_area=min_area,
                                            max_area=max_area,
                                            draw_contours=draw_contours
                                        )
    return final, contours, meas_last, meas_now
    

colours = [(0,0,255), (0,255,0), (255,0,0), (255,0,255), (0,255,255), (255,255,0), (0,0,0), (255,255,255)]*10
def cleanup_centroids(final, contours, n_inds,
                        meas_last, meas_now,
                        mot, frame_index,
                        draw_circles=False,
                        use_kmeans = True
                    ):#yeh mot kya hai?
    """
    Cleans up and associates detected centroids with tracked objects using k-means and the Hungarian algorithm.

    Args:
        final (np.ndarray): Frame on which to draw results.
        contours (list): List of detected contours.
        n_inds (int): Number of expected individuals to track.
        meas_last (list): List of centroids from the previous frame.
        meas_now (list): List of centroids from the current frame.
        mot (bool): Whether to apply object tracking logic.
        frame_index (int): Index of the current frame (used for labeling or logging).
        draw_circles (bool, default=False): Whether to draw circles on tracked centroids.
        use_kmeans (bool, default=True): Whether to apply k-means clustering when count mismatches.

    Returns:
        processed frame, updated meas_now with consistent ordering
    """

    if use_kmeans\
            and len(meas_now) != n_inds\
            and len(meas_now) > 0\
            and n_inds > 1:

        contours, meas_now = tr.apply_k_means(contours, n_inds, meas_now)

    #if len(meas_now) == len(meas_last) and len(meas_now) > 1:
    if len(meas_now) > 0 and len(meas_last) > 0:
        row_ind, col_ind = tr.hungarian_algorithm(meas_last, meas_now)
        final, meas_now = tr.reorder_and_draw(final, colours, n_inds,
                                                    col_ind, meas_now, mot, 
                                                    frame_index,
                                                    draw_circles=draw_circles
                                                )
    return final, meas_now


if __name__ == "__main__":
    print("Running toy tracker using these functions.")
    video_directory = "/Users/vivekhsridhar/Library/Mobile Documents/com~apple~CloudDocs/Documents/Code/Python/OpenCV/tracktor"

    vidfile = joinpath(video_directory, "videos", "fish_video.mp4")
    cap = get_vid(vidfile)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    output_framesize = (int(cap.read()[1].shape[1]),
                            int(cap.read()[1].shape[0]))
    out = cv2.VideoWriter(filename = joinpath(video_directory, "output", "trial.mp4"),
                            fourcc = fourcc,
                            fps = 30.0,
                            frameSize = output_framesize,
                            isColor = True
                        )


    meas_last = [[0, 0]]
    meas_now = [[0, 0]]

    while True:
        try:
            frame, frame_index = get_frame(cap)
            print(frame_index, end="\033[K\r")
        except VideoEndedError:
            print("File completed")
            quit()

        final, contours, meas_last, meas_now = get_contours(
                                frame,
                                meas_last=meas_last,
                                meas_now=meas_now,
                                min_area=1000,
                                max_area=10000,
                                block_size=81,
                                offset=38,
                                scaling=1.0,
                                draw_contours=True
                            )

        final, meas_now = cleanup_centroids(
                            final=final,
                            contours=contours,
                            n_inds=1,
                            meas_last=meas_last,
                            meas_now=meas_now,
                            mot=True,
                            frame_index=frame_index,
                            draw_circles=True,
                            use_kmeans = True
                        )

        out.write(final)
    out.release()
