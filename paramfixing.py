import argparse
import cv2
import os
import re
import numpy as np
import warnings
from os.path import join as joinpath
import importlib

import tracktor as tr
import params


def parse_arguments():
    parser = argparse.ArgumentParser(description="Video analysis and threshold tuning.")

    parser.add_argument('-n', '--name', required=True, help='Name of the new video file after analysis')
    parser.add_argument('-c', '--camera', help='Camera device number')
    parser.add_argument('-f', '--file', help='Complete file path')

    # Video parameters
    parser.add_argument('-res', '--resolution', default="1920x1080",
                        help='Resolution (e.g. 1920x1080). Needed for accurate plotting.')
    parser.add_argument('-x', '--xdistance',
                        help='Real-world distance in cm covered by the video along the X-axis')
    parser.add_argument('-fps', '--fps', default=30, type=int,
                        help='Frames per second (default: 30)')

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


def process_image(image, block_size, offset, min_blob_size, max_blob_size):
    current_image = image.copy()
    block_size = max(3, block_size | 1)  # Ensure it's odd

    thresh = tr.colour_to_thresh(current_image, block_size=block_size,
                                 offset=offset, blur=False, invert=False)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for contour in contours:
        area = cv2.contourArea(contour)
        if min_blob_size < area < max_blob_size:
            cv2.drawContours(current_image, [contour], -1, (0, 255, 0), 2)
            M = cv2.moments(contour)
            if M["m00"]:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
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

        with open('params.py', 'r', encoding='utf-8') as file:
            data = file.readlines()

        data[2] = f"block_size = {block_size}\n"
        data[3] = f"offset = {offset}\n"
        data[10] = f"min_area = {min_blob_size}\n"
        data[11] = f"max_area = {max_blob_size}\n"

        with open('params.py', 'w', encoding='utf-8') as file:
            file.writelines(data)

        importlib.reload(params)
        print("Parameters updated in params.py")


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

    xdist = int(args.xdistance) if args.xdistance else None
    fps = int(args.fps)

    # Extract first frame
    if args.file:
        extract_first_frame_from_file(args.file)
    else:
        extract_first_frame_from_camera(int(args.camera))

    image_path = joinpath(os.getcwd(), 'first_frame.jpg')
    image = cv2.imread(image_path)

    # Initialize parameters
    initial_block_size = 51
    initial_offset = 0
    initial_min_blob_size = 1000
    initial_max_blob_size = 10000

    cv2.namedWindow('Threshold Parameters')
    cv2.createTrackbar('Block size', 'Threshold Parameters', initial_block_size, 81, lambda x: None)
    cv2.createTrackbar('Offset', 'Threshold Parameters', initial_offset, 50, lambda x: None)
    cv2.createTrackbar('Min blob size', 'Threshold Parameters', 0, 1000, lambda x: None)
    cv2.createTrackbar('Max blob size', 'Threshold Parameters', 0, 10000, lambda x: None)

    process_image(image, initial_block_size, initial_offset,
                  initial_min_blob_size, initial_max_blob_size)

    while True:
        key = cv2.waitKey(1) & 0xFF
        if key in [27, ord('q')]:
            break

        block_size = cv2.getTrackbarPos('Block size', 'Threshold Parameters')
        offset = cv2.getTrackbarPos('Offset', 'Threshold Parameters')
        min_blob_size = cv2.getTrackbarPos('Min blob size', 'Threshold Parameters')
        max_blob_size = cv2.getTrackbarPos('Max blob size', 'Threshold Parameters')

        process_image(image, block_size, offset, min_blob_size, max_blob_size)

    cv2.destroyAllWindows()

    block_size = block_size | 1  # Ensure block size is odd
    update_params_file(block_size, offset, min_blob_size, max_blob_size,
                       initial_block_size, initial_offset,
                       initial_min_blob_size, initial_max_blob_size)


if __name__ == "__main__":
    main()
