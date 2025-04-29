
# Pranav Minasandra
# 29 Apr 2025
# pminasandra.github.io

"""
Example code that triggers when an individual is within a certain part of the screen
"""

import serial

import tracktorlive as trl


client = trl.spawn_trclient("mouseinthehouse")
ser = serial.Serial('/dev/ttyACM0')

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

    if _in_rect(curr_loc):#If the mouse is in the specified area
        if not _in_rect(prev_loc):
            ser.write(b'm')


trl.run_trclient(client)
ser.close()
