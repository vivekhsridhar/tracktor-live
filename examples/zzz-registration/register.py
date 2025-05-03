import json
from os.path import join as joinpath
import os

import cv2
import numpy as np

import tracktorlive as trl


CROP_WIDTH, CROP_HEIGHT = 200, 200
CROPPED_DIR = "centered-clips"
os.makedirs(CROPPED_DIR, exist_ok=True)

with open("fish-params.json") as f:
    params = json.load(f)
params["fps"] = 30

server, semm = trl.spawn_trserver(
                "fish_video.mp4",
                params,
                n_ind=1,
                feed_id="fish_video",
                realtime=False
)

@server
def crop_to_center(server):
    data, _ = server.get_data_and_clock()
    pos = data[0, :, -1]

    if np.any(np.isnan(pos)):
        return

    if np.any(pos < 0):
        return

    x, y = int(pos[0]), int(pos[1])
    frame = server.current_frame
    h, w = frame.shape[:2]

    x1 = max(x - CROP_WIDTH // 2, 0)
    y1 = max(y - CROP_HEIGHT // 2, 0)
    x2 = min(x1 + CROP_WIDTH, w)
    y2 = min(y1 + CROP_HEIGHT, h)
    x1 = max(x2 - CROP_WIDTH, 0)
    y1 = max(y2 - CROP_HEIGHT, 0)

    crop = frame[y1:y2, x1:x2]
    if crop.shape[:2] != (CROP_HEIGHT, CROP_WIDTH):
        return

    if not hasattr(server, "crop_writer") or server.crop_writer is None:
        outpath = joinpath(CROPPED_DIR, f"centered-{server.feed_id}.avi")
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        server.crop_writer = cv2.VideoWriter(outpath, fourcc, server.fps, (CROP_WIDTH, CROP_HEIGHT))

    server.crop_writer.write(crop)

@server.stopfunc
def close_crop_writer(server):
    if hasattr(server, "crop_writer") and server.crop_writer is not None:
        server.crop_writer.release()
        server.crop_writer = None

trl.run_trsession(server, semm)

