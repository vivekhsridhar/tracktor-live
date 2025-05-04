import json
import multiprocessing as mp
from os.path import join as joinpath
import os
mp.set_start_method('fork')

import cv2
import numpy as np

import tracktorlive as trl



with open("termite-params.json") as f:
    params = json.load(f)
params["fps"] = 30

server, semm = trl.spawn_trserver(
                "../zzz-registration/termite_video.mp4",
                params,
                n_ind=8,
                feed_id="termite_video",
                realtime=False,
                draw=True,
                write_video=True
)

trl.run_trsession(server, semm)

