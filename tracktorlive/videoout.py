# Pranav Minasandra
# 24 Apr 2025
# pminasandra.github.io

import multiprocessing as mp

import cv2

def vidout(frames, filename, fps, framesize):
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
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

def prl_vidout(frames, filename, fps, framesize):
    proc = mp.Process(target=vidout, args=(frames, filename, fps, framesize))
    proc.start()
    proc.close()
