# Pranav Minasandra
# 29 Apr 2025
# pminasandra.github.io

"""
Example code that triggers when an individual is within a certain part of the screen
"""

import json

import cv2

import tracktorlive as trl

with open("mouse-params.json") as f:
    params = json.load(f)
params["fps"] = 30

server, semm = trl.spawn_trserver("./mouse_video.mp4",
                                params=params,
                                n_ind = 1,
                                realtime=False,
                                buffer_size = 1,
                                draw=True,
                                feed_id="mouseinthehouse"
                            )

top_left = (150, 50)
bottom_right = (300, 200)
color = (0, 255, 0)  # Green
alpha = 0.5  # Transparency factor: 0.0 = fully transparent, 1.0 = fully opaque

# Draw rectangle on the overlay

@server
def show(server):
    if server.framesbuffer[-1] is None:
        return None
    fr = server.framesbuffer[-1].copy()
    cv2.rectangle(fr, top_left, bottom_right, color, thickness=-1)
    cv2.imshow('tracking', fr)

    cv2.waitKey(1)

trl.run_trserver(server, semm)
