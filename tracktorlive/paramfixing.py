# Isaac Planas-Sitja, Pranav Minasandra and Vivek H Sridhar
# 14 Apr 2025

import os
import re
import argparse
import json
import cv2
import numpy as np

# from . import tracktor as tr
import tracktor as tr

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


def extract_first_frame_from_file(path):
    """
    Extracts and saves the first frame from a video file.
    
    Args:
        path (str): Path to the video file.
    """
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise IOError("Could not open video file.")
    ret, frame = cap.read()
    cap.release()
    if not ret:
        raise IOError("Could not read frame from video file.")
    cv2.imwrite('first_frame.jpg', frame)
    print("First frame saved as 'first_frame.jpg'")


def extract_first_frame_from_camera(device_index):
    """
    Captures a frame from a live camera feed and saves it.
    
    Args:
        device_index (int): Index of the camera device.
    """
    cap = cv2.VideoCapture(device_index)
    if not cap.isOpened():
        raise IOError("Cannot open camera.")

    print("Press 'q' or ESC to quit preview early.")
    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        cv2.imshow('Live Feed', frame)
        frame_count += 1
        key = cv2.waitKey(1) & 0xFF
        if frame_count == 100 or key in [27, ord('q')]:
            cv2.imwrite('first_frame.jpg', frame)
            print("First frame saved as 'first_frame.jpg'")
            break

    cap.release()
    cv2.destroyAllWindows()


def process_image(image, block_size, offset, min_blob_size, max_blob_size, invert):
    """
    Processes an image using adaptive thresholding and contour detection.
    
    Args:
        image (ndarray): Source image.
        block_size (int): Adaptive threshold block size.
        offset (int): Offset for thresholding.
        min_blob_size (int): Minimum contour area to display.
        max_blob_size (int): Maximum contour area to display.
        invert (bool): Whether to invert thresholding.
    """
    current_image = image.copy()
    block_size = max(3, block_size | 1)  # Ensure block size is odd

    # Generate binary mask
    thresh = tr.colour_to_thresh(current_image, block_size=block_size,
                                 offset=offset, blur=False, invert=bool(invert))

    # Find external contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for contour in contours:
        area = cv2.contourArea(contour)
        if min_blob_size < area < max_blob_size:
            cv2.drawContours(current_image, [contour], -1, (0, 0, 255), 2)
            moments = cv2.moments(contour)
            if moments["m00"]:
                cx = int(moments["m10"] / moments["m00"])
                cy = int(moments["m01"] / moments["m00"])
                cv2.putText(current_image, f'{int(area)}', (cx - 20, cy),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    cv2.imshow('Threshold Image', current_image)


def update_params_file(block_size, offset, min_blob_size, max_blob_size, invert, 
                       initial_block_size, initial_offset,
                       initial_min_blob_size, initial_max_blob_size,
                       initial_invert, write_file=False):
    """
    Updates the params.json file if any of the parameters have changed.
    
    Args:
        block_size, offset, min_blob_size, max_blob_size, invert: Current values.
        initial_*: Corresponding initial values.
    """
    if (block_size != initial_block_size or
        offset != initial_offset or
        min_blob_size != initial_min_blob_size or
        max_blob_size != initial_max_blob_size or
        invert != initial_invert):

        config = {
            "block_size": block_size,
            "offset": offset,
            "min_area": min_blob_size,
            "max_area": max_blob_size,
            "invert": invert
        }

        if write_file:
            with open("params.json", "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)

            print("Parameters updated in params.json")
        return config


def gui_set_params(cap,
                    vidtype,
                    block_size_max=151,
                    offset_max=100,
                    min_blob_size_max=5000,
                    max_blob_size_max=50000,
                    write_file=False):
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
    initial_invert = 1
    
    is_paused = False
    frame_index = 0

    # Get total frames to set max for seek bar
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Create GUI sliders
    cv2.namedWindow('Threshold Parameters', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Threshold Parameters', 1000, 80)

    cv2.createTrackbar('Block size', 'Threshold Parameters', initial_block_size, block_size_max, lambda x: None)
    cv2.createTrackbar('Offset', 'Threshold Parameters', initial_offset, offset_max, lambda x: None)
    cv2.createTrackbar('Min blob size', 'Threshold Parameters', initial_min_blob_size, min_blob_size_max, lambda x: None)
    cv2.createTrackbar('Max blob size', 'Threshold Parameters', initial_max_blob_size, max_blob_size_max, lambda x: None)
    cv2.createTrackbar('Invert', 'Threshold Parameters', initial_invert, 1, lambda x: None)

    if vidtype=="file":
        cv2.createTrackbar('Seek', 'Threshold Parameters', 0, total_frames - 1, lambda x: None)

    while True:
        if not is_paused:
            ret, frame = cap.read()
            if not ret:
                break
            frame_index = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
            cv2.setTrackbarPos('Seek', 'Threshold Parameters', frame_index)

        else:
            # If paused and user moves the trackbar, fetch frame at that index
            seek_pos = cv2.getTrackbarPos('Seek', 'Threshold Parameters')
            if seek_pos != frame_index:
                cap.set(cv2.CAP_PROP_POS_FRAMES, seek_pos)
                ret, frame = cap.read()
                if not ret:
                    break
                frame_index = seek_pos

        # Get parameter values
        block_size = cv2.getTrackbarPos('Block size', 'Threshold Parameters')
        offset = cv2.getTrackbarPos('Offset', 'Threshold Parameters')
        min_blob_size = cv2.getTrackbarPos('Min blob size', 'Threshold Parameters')
        max_blob_size = cv2.getTrackbarPos('Max blob size', 'Threshold Parameters')
        invert = cv2.getTrackbarPos('Invert', 'Threshold Parameters')

        process_image(frame, block_size, offset, min_blob_size, max_blob_size, invert)

        key = cv2.waitKey(100) & 0xFF
        if key in [27, ord('q')]:
            break
        elif key == ord(' '):  # Spacebar toggles play/pause
            is_paused = not is_paused

    cv2.destroyAllWindows()

    # Ensure odd block size before saving
    block_size = block_size | 1

    # Update config file if values changed
    configdict = update_params_file(block_size, offset, min_blob_size, max_blob_size,
                       initial_block_size, initial_offset,
                       initial_min_blob_size, initial_max_blob_size,
                       invert, initial_invert, write_file=write_file)

    return configdict


def main():
    args = parse_arguments()

    if args.file and args.camera:
        raise SyntaxError("Specify either a video file or camera, not both.")
    if not args.file and not args.camera:
        raise SyntaxError("You must specify a video file (-f) or camera (-c).")

    # Initialize video capture from file or camera
    if args.file:
        cap = cv2.VideoCapture(args.file)
    else:
        cap = cv2.VideoCapture(int(args.camera))

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
