# Pranav Minasandra
# 24 Apr 2025
# pminasandra.github.io

import multiprocessing as mp

import cv2

def vidout(frames, filename, fps, framesize, codec):
    """
    Writes a sequence of video frames to a video file using OpenCV.

    Args:
        frames (list of ndarray): A list of video frames (NumPy arrays) to be written.
        filename (str): Path to the output video file.
        fps (float): Frames per second for the output video.
        framesize (tuple): Size of the video frames as (width, height).

    Raises:
        AssertionError: If the video writer fails to open the file.
    """
    fourcc = cv2.VideoWriter_fourcc(*codec)
    vidout = cv2.VideoWriter(
                            filename=filename,
                            fourcc = fourcc,
                            fps = fps,
                            frameSize = framesize,
                            isColor = True
                        )
    assert vidout.isOpened()
    for frame in frames:
        vidout.write(frame)
    vidout.release()

def prl_vidout(frames, filename, fps, framesize, codec):
    """
    Launches a parallel process to write video frames to a file using `vidout`.

    Args:
        frames (list of ndarray): List of frames to be written to the video.
        filename (str): Path to the output video file.
        fps (float): Frames per second for the output video.
        framesize (tuple): Size of the video frames as (width, height).
        codec (str): e.g., XVID, DIVX, mp4v, etc.

    Notes:
        This function uses `multiprocessing` to offload the writing process,
        which can be useful to avoid blocking the main execution thread.
    """
    proc = mp.Process(target=vidout, args=(frames, filename, fps, framesize, codec))
    proc.start()
