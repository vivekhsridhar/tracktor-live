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

import config
import tracktor as tr

def get_vid(source, vidtype="cam"):
    """
    Gets a cv2.VideoCapture object from given source
    Args:
        source (int or str): filename or camera device number
        vidtype (str, default "cam"): {"cam", "file"}
    Returns:
        cv2.VideoCapture object
    """

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

    ret, frame = cap.read()
    if not ret:
        raise EOFError("frame could not be obtained")
    frame_index = cap.get(1)

    return frame, frame_index


def get_contours(frame, block_size,
                    meas_last, meas_now,
                    min_area, max_area,
                    offset, scaling,
                    draw_contours=False
                ):
    """
    bla bla
    """
    # FIXME: write docstring

    frame = cv2.resize(frame,
                            None,
                            fx=scaling,
                            fy=scaling,
                            interpolation=cv2.INTER_LINEAR
                        )
    thresh = tr.colour_to_thresh(frame, block_size, offset)
    final, contours, meas_last, meas_now = tr.detect_and_draw_contours(
                                            frame,
                                            thresh,
                                            meas_last,
                                            meas_now,
                                            min_area,
                                            max_area,
                                            draw_contours=draw_contours
                                        )
    return final, contours, meas_last, meas_now
    

colours = [(255,255,255)]*10
def cleanup_centroids(final, contours, n_inds,
                        meas_last, meas_now,
                        mot, frame_index,
                        draw_circles=False,
                        use_kmeans = True
                    ):#yeh mot kya hai?
    """
    blablabla
    """

    if use_kmeans\
            and len(meas_now) != n_inds\
            and n_inds > 1:
# FIXME: write docstring

        contours, meas_now = tr.apply_k_means(contours, n_inds, meas_now)

    row_ind, col_ind = tr.hungarian_algorithm(meas_last, meas_now)
    final, meas_now= tr.reorder_and_draw(final, colours, n_inds,
                                                col_ind, meas_now, mot, 
                                                frame_index,
                                                draw_circles=draw_circles
                                            )

    return final, meas_now


def make_numpy_frame(meas_now, n_ind):
    n_available = len(meas_now)
    arr = np.ndarray((n_ind, 2), dtype=np.float64)
    arr[:,:] = np.nan
    arr[:n_available, :] = meas_now
    # assuming of course that n_available > n_ind

    return arr


if __name__ == "__main__":
    print("Running toy tracker using these functions.")
    vidfile = joinpath(config.DATA, "vids", "fish_video.mp4")
    cap = get_vid(vidfile, vidtype="file")
    fourcc = cv2.VideoWriter_fourcc(*'DIVX')
    output_framesize = (int(cap.read()[1].shape[1]*1.0),
                            int(cap.read()[1].shape[0]*1.0))
    out = cv2.VideoWriter(filename = joinpath(config.DATA, "trial.mp4"),
                            fourcc = fourcc,
                            fps = 30.0,
                            frameSize = output_framesize,
                            isColor = True
                        )


    while True:
        try:
            frame, frame_index = get_frame(cap)
        except EOFError:
            print("File completed")
            quit()

        meas_last = [[0, 0]]
        meas_now = [[0, 0]]

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
