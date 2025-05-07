# Isaac Planas-Sitja, Pranav Minasandra and Vivek H Sridhar
# 14 Apr 2025

import os
import re
import argparse
import json
import cv2
import numpy as np

from . import trackutils as tru

def parse_arguments():
    """
    Parses command-line arguments for video analysis and threshold tuning.
    
    Returns:
        argparse.Namespace: Parsed arguments object.
    """
    parser = argparse.ArgumentParser(description="Video analysis and threshold tuning.")

    parser.add_argument('-c', '--camera', help='Camera device number')
    parser.add_argument('-f', '--file', help='Complete file path')

    # Trackbar range settings
    parser.add_argument('--block-size-max', type=int, default=151,
                        help='Maximum block size (must be odd)')
    parser.add_argument('--offset-max', type=int, default=100,
                        help='Maximum offset value')
    parser.add_argument('--min-blob-size-max', type=int, default=5000,
                        help='Maximum value for min blob size trackbar')
    parser.add_argument('--max-blob-size-max', type=int, default=50000,
                        help='Maximum value for max blob size trackbar')

    return parser.parse_args()


def process_image(image, block_size, offset, min_blob_size, max_blob_size, img_invert):
    """
    Processes an image using adaptive thresholding and contour detection.
    
    Args:
        image (ndarray): Source image.
        block_size (int): Adaptive threshold block size.
        offset (int): Offset for thresholding.
        min_blob_size (int): Minimum contour area to display.
        max_blob_size (int): Maximum contour area to display.
        img_invert (bool): Whether to invert thresholding.
    """
    current_image = image.copy()
    block_size = max(3, block_size | 1)  # Ensure block size is odd

    # Generate binary mask
    processed_image, contours, meas_last, meas_now = tru.get_contours(current_image, block_size=block_size, 
                                                                    meas_last=None, meas_now=None, 
                                                                    min_area=min_blob_size, max_area=max_blob_size, 
                                                                    offset=offset, scaling=1.0, 
                                                                    fps=None, invert=bool(img_invert), draw_contours=True)

    cv2.imshow('Threshold Image', processed_image)


def update_params_file(block_size, offset, min_blob_size, max_blob_size, img_invert, 
                       initial_block_size, initial_offset,
                       initial_min_blob_size, initial_max_blob_size,
                       initial_img_invert, fps=None, write_file=None):
    """
    Updates the params.json file if any of the parameters have changed.
    
    Args:
        block_size, offset, min_blob_size, max_blob_size, img_invert: Current values.
        initial_*: Corresponding initial values.
    """

    if (block_size != initial_block_size or
        offset != initial_offset or
        min_blob_size != initial_min_blob_size or
        max_blob_size != initial_max_blob_size or
        img_invert != initial_img_invert):

        config = {
            "block_size": block_size,
            "offset": offset,
            "min_area": min_blob_size,
            "max_area": max_blob_size,
            "invert": img_invert,
            "fps": fps
        }

        if write_file is not None:
            with open(write_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)

            print(f"Parameters updated in {write_file}")
    else:
        config ={
            "block_size":   initial_block_size,
            "offset":       initial_offset,
            "min_area":     initial_min_blob_size,
            "max_area":     initial_max_blob_size,
            "invert":   initial_img_invert,
            "fps": fps
        }
    return config


def gui_set_params(cap,
                    vidtype,
                    block_size_max=151,
                    offset_max=100,
                    min_blob_size_max=5000,
                    max_blob_size_max=50000,
                    write_file=None):
    """
    Main function to handle GUI threshold tuning and contour display.
    """
    if not cap.isOpened():
        raise IOError("Failed to open video source.")

    # Initial parameter values
    initial_block_size = 51
    initial_offset = 0
    initial_min_blob_size = 500
    initial_max_blob_size = 5000
    initial_img_invert = 1
    
    is_paused = False
    frame_index = 0

    # Get total frames to set max for seek bar
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Create GUI sliders
    cv2.namedWindow('Tracking Parameters', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Tracking Parameters', 1000, 80)

    cv2.createTrackbar('Block size', 'Tracking Parameters', initial_block_size, block_size_max, lambda x: None)
    cv2.createTrackbar('Offset', 'Tracking Parameters', initial_offset, offset_max, lambda x: None)
    cv2.createTrackbar('Min blob size', 'Tracking Parameters', initial_min_blob_size, min_blob_size_max, lambda x: None)
    cv2.createTrackbar('Max blob size', 'Tracking Parameters', initial_max_blob_size, max_blob_size_max, lambda x: None)
    cv2.createTrackbar('Image invert', 'Tracking Parameters', initial_img_invert, 1, lambda x: None)

    if vidtype=="file":
        cv2.createTrackbar('Seek', 'Tracking Parameters', 0, total_frames - 1, lambda x: None)

    while True:
        if not is_paused:
            try:
                frame, frame_index = tru.get_frame(cap)
            except:
                print("Video complete. Looping back to the start.")
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                frame, frame_index = tru.get_frame(cap)
                
            cv2.setTrackbarPos('Seek', 'Tracking Parameters', int(frame_index))

        else:
            # If paused and user moves the trackbar, fetch frame at that index
            seek_pos = cv2.getTrackbarPos('Seek', 'Tracking Parameters')
            if seek_pos != frame_index:
                cap.set(cv2.CAP_PROP_POS_FRAMES, seek_pos)
                try:
                    frame, frame_index = tru.get_frame(cap)
                except:
                    print("Video complete")

        # Get parameter values
        block_size = cv2.getTrackbarPos('Block size', 'Tracking Parameters')
        offset = cv2.getTrackbarPos('Offset', 'Tracking Parameters')
        min_blob_size = cv2.getTrackbarPos('Min blob size', 'Tracking Parameters')
        max_blob_size = cv2.getTrackbarPos('Max blob size', 'Tracking Parameters')
        img_invert = cv2.getTrackbarPos('Image invert', 'Tracking Parameters')

        process_image(frame, block_size, offset, min_blob_size, max_blob_size, img_invert)

        key = cv2.waitKey(100) & 0xFF
        if key in [27, ord('q')]:
            break
        elif key == ord(' '):  # Spacebar toggles play/pause
            is_paused = not is_paused

    cv2.destroyAllWindows()

    # Ensure odd block size before saving
    block_size = block_size | 1

    # Update config file if values changed
    fps = cap.get(cv2.CAP_PROP_FPS)
    configdict = update_params_file(block_size, offset, min_blob_size, max_blob_size,
                                    img_invert, initial_block_size, initial_offset,
                                    initial_min_blob_size, initial_max_blob_size,
                                    initial_img_invert, fps=fps, write_file=write_file)

    return configdict


def main():
    args = parse_arguments()

    if args.file and args.camera:
        raise SyntaxError("Specify either a video file or camera, not both.")
    if not args.file and not args.camera:
        raise SyntaxError("You must specify a video file (-f) or camera (-c).")

    # Initialize video capture from file or camera
    if args.file:
        cap = tru.get_vid(args.file)
    else:
        cap = tru.get_vid(int(args.camera))

    vidtype = "cam"
    if args.file:
        vidtype = "file"
    configdict = gui_set_params(cap=cap,
                    vidtype=vidtype,
                    block_size_max=args.block_size_max,
                    offset_max=args.offset_max,
                    min_blob_size_max=args.min_blob_size_max,
                    max_blob_size_max=args.max_blob_size_max,
                    write_file=True)

    cap.release()

if __name__ == "__main__":

    main()
