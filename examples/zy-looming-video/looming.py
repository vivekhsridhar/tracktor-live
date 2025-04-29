
"""
Example script to chunk video data only when animals approach close by.
"""

import multiprocessing as mp
import os
from os.path import join as joinpath
mp.set_start_method('fork')

import json
import numpy as np
import ulid

import tracktorlive as trl

# This demonstrates how to chunk input from video sources, retaining
# only videos where animals are in proximity. Here we will use a video,
# but this is only for demonstration. This is practically intended for
# cases when interactions are rare and a real-time tracktorserver is run.
# In this video example, we use Zerg Ultralisks engaging in combat, a common
# scene from the video game Starcaft: Brood War (1998) to act as a proxy for
# animal interactions.

# First, let's load the parameters.
with open("flume-video-params.json") as f:
    params = json.load(f)
params["fps"] = 30.0
#
#THRESH_APPROACH_DIST = 300 #px
MIN_RECORDED_ITERS = 30
#os.makedirs("ultralisks-chunked", exist_ok=True)
#

server, semm = trl.spawn_trserver("./flume_video.mp4",
                                    params=params,
                                    n_ind=1,
                                    realtime=False,
                                    buffer_size=2#just need a second before interactions
                                )

## We will now write a function to do the chunking based on this distance:
@server#adding this decorator makes this a server-side casette
def print_vel(server):
    data, clock = server.get_data_and_clock()

    nonnandat = sum(data[~np.isnan(data)])
    if nonnandat < MIN_RECORDED_ITERS*2:
        return None
    data = data[:,:,-MIN_RECORDED_ITERS:]
    clock = clock[-MIN_RECORDED_ITERS:]
    if np.any(data < 0):
        return None
    else:
        dX_Y = data[:,:,-1] - data[:,:,-2]
        dR = (dX_Y**2).sum()
        v = dR/(clock[-1] - clock[-2])

        print(dR, "\n")


#def chunking(server):
#    data, _ = server.get_data_and_clock()
#    curr_vals = data[:,:,-1]
#
#    if np.any(curr_vals < 0.0):
#        # we don't know the location of some individuals
#        return None
#
#    dist = np.sqrt(((curr_vals[0,:] - curr_vals[1,:])**2).sum())
#    if dist <= THRESH_APPROACH_DIST:
#        if len(server.recorded_frames) == 0:#nothing stored yet?
#            server.keep_video.value = True
#    elif dist > THRESH_APPROACH_DIST:
#        if len(server.recorded_frames) > 0:
#            server.keep_video.value=False
#            fname = f'chunk-{ulid.ULID()}.avi'
#            server.dumpvideo(joinpath('ultralisks-chunked', fname))
#
## Since this is recording from a video, we need to handle end-of-file events
## However, this bit isn't relevant in real-time applications.
#@server.stopfunc#adding this decorator makes it a server-side termination functionality
#def final_chunk(server):
#    if len(server.recorded_frames) > 0:
#        server.keep_video.value=False
#        fname = f'chunk-{ulid.ULID()}.avi'
#        server.dumpvideo(joinpath('ultralisks-chunked', fname))
#
trl.run_trserver(server, semm)
