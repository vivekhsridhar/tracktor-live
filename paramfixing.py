import os
import re
import argparse
import warnings
import numpy as np


import json
import cv2

import tracktor as tr


def parse_arguments():
    parser = argparse.ArgumentParser(description="Video analysis and threshold tuning.")

    parser.add_argument('-n', '--name', required=True, help='Name of the new video file after analysis')
    parser.add_argument('-c', '--camera', help='Camera device number')
    parser.add_argument('-f', '--file', help='Complete file path')

    # Video parameters
    parser.add_argument('-res', '--resolution', default="1920x1080",
                        help='Resolution (e.g. 1920x1080). Needed for accurate plotting.')
    parser.add_argument('-fps', '--fps', default=30, type=int,
                        help='Frames per second (default: 30)')

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


def parse_resolution(res_string):
    try:
        width = int(re.search(r'\d+', res_string).group())
        height = int(re.search(r'\d+$', res_string).group())
        return width, height
    except:
        raise ValueError("Invalid resolution format. Use WIDTHxHEIGHT (e.g., 1920x1080).")


def extract_first_frame_from_file(path):
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
    current_image = image.copy()
    block_size = max(3, block_size | 1)  # Ensure it's odd

    thresh = tr.colour_to_thresh(current_image, block_size=block_size,
                             offset=offset, blur=False, invert=bool(invert))

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for contour in contours:
        area = cv2.contourArea(contour)
        if min_blob_size < area < max_blob_size:
            cv2.drawContours(current_image, [contour], -1, (0, 0, 255), 1)
            moments = cv2.moments(contour)
            if moments["m00"]:
                cx = int(moments["m10"] / moments["m00"])
                cy = int(moments["m01"] / moments["m00"])
                cv2.putText(current_image, f'{int(area)}', (cx - 20, cy),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

    cv2.imshow('Threshold Image', current_image)


def update_params_file(block_size, offset, min_blob_size, max_blob_size,
                       initial_block_size, initial_offset,
                       initial_min_blob_size, initial_max_blob_size):
    if (block_size != initial_block_size or
        offset != initial_offset or
        min_blob_size != initial_min_blob_size or
        max_blob_size != initial_max_blob_size):

        config = {
            "block_size": block_size,
            "offset": offset,
            "min_area": min_blob_size,
            "max_area": max_blob_size
        }

        with open("params.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)

        print("Parameters updated in params.json")


def main():
    args = parse_arguments()

    if args.file and args.camera:
        raise SyntaxError("Specify either a video file or camera, not both.")
    if not args.file and not args.camera:
        raise SyntaxError("You must specify a video file (-f) or camera (-c).")

    try:
        xmax, ymax = parse_resolution(args.resolution)
    except ValueError as e:
        print(e)
        return

    fps = int(args.fps)

    # Extract first frame
    if args.file:
        extract_first_frame_from_file(args.file)
    else:
        extract_first_frame_from_camera(int(args.camera))

    image_path = os.path.join(os.getcwd(), 'first_frame.jpg')
    image = cv2.imread(image_path)

    # Initialize parameters
    initial_block_size = 51
    initial_offset = 0
    initial_min_blob_size = 500
    initial_max_blob_size = 5000
    initial_invert = 0

    cv2.namedWindow('Threshold Parameters')
    cv2.createTrackbar('Block size', 'Threshold Parameters', initial_block_size, args.block_size_max, lambda x: None)
    cv2.createTrackbar('Offset', 'Threshold Parameters', initial_offset, args.offset_max, lambda x: None)
    cv2.createTrackbar('Min blob size', 'Threshold Parameters', initial_min_blob_size, args.min_blob_size_max, lambda x: None)
    cv2.createTrackbar('Max blob size', 'Threshold Parameters', initial_max_blob_size, args.max_blob_size_max, lambda x: None)
    cv2.createTrackbar('Invert', 'Threshold Parameters', 0, 1, lambda x: None)

    process_image(image, initial_block_size, initial_offset,
                  initial_min_blob_size, initial_max_blob_size, initial_invert)

    while True:
        key = cv2.waitKey(1) & 0xFF
        if key in [27, ord('q')]:
            break

        block_size = cv2.getTrackbarPos('Block size', 'Threshold Parameters')
        offset = cv2.getTrackbarPos('Offset', 'Threshold Parameters')
        min_blob_size = cv2.getTrackbarPos('Min blob size', 'Threshold Parameters')
        max_blob_size = cv2.getTrackbarPos('Max blob size', 'Threshold Parameters')
        invert = cv2.getTrackbarPos('Invert', 'Threshold Parameters')

        process_image(image, block_size, offset, min_blob_size, max_blob_size, invert)

    cv2.destroyAllWindows()

    block_size = block_size | 1  # Ensure block size is odd
    update_params_file(block_size, offset, min_blob_size, max_blob_size,
                       initial_block_size, initial_offset,
                       initial_min_blob_size, initial_max_blob_size)


if __name__ == "__main__":
    main()
