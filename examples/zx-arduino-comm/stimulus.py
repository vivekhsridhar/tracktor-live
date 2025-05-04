# Pranav Minasandra
# 29 Apr 2025
# pminasandra.github.io

"""
Example code that triggers when an individual is within a certain part of the screen
"""

import json
import multiprocessing as mp
mp.set_start_method('fork')

import cv2
import serial
import serial.tools.list_ports

import tracktorlive as trl


def find_arduino_port():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        desc = port.description.lower()
        manu = (port.manufacturer or "").lower()
        if 'arduino' in desc or 'arduino' in manu:
            return port.device
    raise RuntimeError('No arduino device could be found')


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
    fr2 = fr.copy()
    cv2.rectangle(fr, top_left, bottom_right, color, thickness=-1)
    cv2.addWeighted(fr, 0.3, fr2, 0.7, 0, fr2)

    cv2.imshow('tracking', fr2)

    cv2.waitKey(1)

client = trl.spawn_trclient("mouseinthehouse")

port = find_arduino_port()
ser = serial.Serial(port, 9600, timeout=1)

top = 50
right = 300
bottom = 200
left = 150

def _in_rect(locs, top=top, right=right, bottom=bottom, left=left):
    return left < locs[0,0] < right and top < locs[0,1] < bottom

@client
def send_to_arduino(data, clock):
    curr_loc = data[:,:,-1]
    prev_loc = data[:,:,-2]

    if _in_rect(curr_loc) and not _in_rect(prev_loc):#mouse just moved into the rectangle
           ser.write(b'm')

trl.run_trsession(server, semm, client)
del client
del server
