
"""
Example script to launch a looming video only when fish is moving.
"""

import multiprocessing as mp
import os
from os.path import join as joinpath
import subprocess
import time
mp.set_start_method('fork')

import cv2
import json
import numpy as np
import ulid

import tracktorlive as trl

# This shows how to setup a server-client system to run a specific command, in
# this case play a video, whenever the animal is moving. The video example is
# motivated by presenting looming stimuli, but any shell command can be added in
# its place, e.g., to run equipment, launch web services, etc. Likewise, any
# condition other than velocity can also be programmed.
# User params:
VEL_CALC_NUM_FRAMES = 5
THRESHOLD_VEL = 125 #px/s
RUN_COMMAND = "cvlc --fullscreen --play-and-exit --no-osd ./looming-video.mp4"
COMMAND_COOLDOWN = 15 #seconds
# Code starts below.


def run_quiet_command(cmd=RUN_COMMAND):
    """Run a bash command quietly and block until it completes."""
    subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=os.environ.copy())


# First, let's load the parameters.
with open("flume-video-params.json") as f:
    params = json.load(f)
params["fps"] = 30.0


#os.makedirs("ultralisks-chunked", exist_ok=True)
#

server, semm = trl.spawn_trserver("./flume_video.mp4",
                                    params=params,
                                    n_ind=1,
                                    realtime=False,
                                    buffer_size=2#just need a second before interactions
                                )

# First, we need to mask out everyhthing outside region of interest
@server#makes this a server-side casette
def mask(server):
    frame = server.current_frame
    mask = np.zeros(frame.shape)
    mask = cv2.rectangle(mask, (280, 3), (1030,690), (255,255,255), -1)
    frame[mask ==  0] = 0

@server#uncomment to show video on screen
def show(server):
    if server.current_frame is None:
        return
    cv2.imshow('tracking', server.current_frame)
    cv2.waitKey(1)

client = trl.spawn_trclient(server.feed_id)

time_last = mp.Value('d', 0.0)

## We will now write a function to do the velocity based video response on this distance:
@client#adding this decorator makes this a client-side casette
def average_speed(data, clock):
    # Extract recent data
    coords = data[0, :, -VEL_CALC_NUM_FRAMES:]  # shape (2, VEL_CALC_NUM_FRAMES)
    times = clock[-VEL_CALC_NUM_FRAMES:]

    # Skip if any coordinates or timestamps are invalid
    if np.isnan(coords).any() or np.isnan(times).any():
        return

    # Compute displacements and distances
    diffs = np.diff(coords, axis=1)  # shape (2, VEL_CALC_NUM_FRAMES-1)
    dists = np.linalg.norm(diffs, axis=0)  # shape (VEL_CALC_NUM_FRAMES-1,)

    dt = times[-1] - times[0]
    if dt > 0:
        avg_speed = np.sum(dists) / dt
    else:
        return

    if avg_speed > THRESHOLD_VEL and time.time() - time_last.value > COMMAND_COOLDOWN:
        time_last.value = time.time()
        run_quiet_command()

trl.run_trsession(server, semm, client)
