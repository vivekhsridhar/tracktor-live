#!/usr/bin/env python
# coding: utf-8

# In[1]:
import numpy as np
import pandas as pd
import os
import sys
import tracktor as tr
import cv2
import scipy.signal
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist
import time
import argparse
#get parameters from the params.py file
import params
import importlib
import math
import subprocess
import re

# ## Global parameters
# This cell (below) enlists user-defined parameters

# In[2]:
parser = argparse.ArgumentParser(description='Introduce parameters.')
parser.add_argument('-n', '--name', required=True, help='Name of new video file after analysis')
parser.add_argument('-c', '--camera', required=False, help='Camera device number')
parser.add_argument('-f', '--file', required=False, help='Complete file path')
parser.add_argument('-d', '--direction', required=False,
                    help='Introduce desired minimal distance in px to move to store direction/angle of individual in real time')
parser.add_argument('-t', '--track', required=False,
                    help='if True, tracktor-live will launch the tracking script to trigger specific actions when objects are in a particular area. If argument is missing, or False, the tracking script will not be used.')

# Video arguments
parser.add_argument('-res', '--resolution', required=False, default="1920x1080",
                    help='Default value is 1920x1080. If different, please introduce video/camera resolution in format "width x height" (e.g. "1920x1200") to convert pixels to cm for final plots. Otherwise pixels will be used for plots.')
parser.add_argument('-x', '--xdistance', required=False,
                    help='Introduce the real distance covered by the video/camera in the X axis to convert distance to cm. Otherwise, the final plots will use 1px = 0.026 cm.')
parser.add_argument('-fps', '--fps', required=False, default=30,
                    help='Default value is 30. If different, please introduce FPS value (frames per second) for accuracy when doing final plots (not required for real-time tracking).')

args = parser.parse_args()

########################################################################
#            Tune parameters
########################################################################

#########################
# Resolution parameters
########################

print('It is recommended to introduce additional parameters (resolution and covered distance in X axis) to improve precision of the final plots. See --help for details.')

#get resolution Width and Height, fps and distance covered in X axis
if args.resolution:
    xmax=int(re.search(r'\d+', args.resolution).group())
    ymax=int(re.search(r'\d+$', args.resolution).group())

fps=int(args.fps)
if args.xdistance:
    xdist=int(args.xdistance)
else:
    xdist=args.xdistance

##############
# video file
##############
if args.file:
    print(f"File path: {args.file}")
    # Path to the video file
    video_path = args.file
    # Open the video file
    video_capture = cv2.VideoCapture(video_path)
    # Check if video opened successfully
    if not video_capture.isOpened():
        print("Error: Could not open video.")
        exit()
    # Read the first frame
    ret, frame = video_capture.read()
    # Check if frame was read successfully
    if ret:
        # Save the frame as an image
        cv2.imwrite('first_frame.jpg', frame)
        print("First frame extracted and saved as 'first_frame.jpg'")
    else:
        print("Error: Could not read frame.")
    # Release the video capture object
    video_capture.release()

##############
# live feed
##############
if args.camera:
    this=0
    print(f"Camera ID: {args.camera}")
    cap = cv2.VideoCapture(int(args.camera))
    if not cap.isOpened():
        print("Cannot open camera. You can try using v4l2-ctl --list-devices or ls /dev/video* to see available devices")
        exit()
    # Read the first frame
    while True:
        ret, frame = cap.read()
        cv2.imshow('live feed',frame)
        this+=1
        # Check if frame was read successfully
        if ret==True and this==100:
            # Save the frame as an image
            cv2.imwrite('first_frame.jpg', frame)
            print("First frame extracted and saved as 'first_frame.jpg'")
            break
        # Break the loop if 'q' or ESC is pressed
        if (cv2.waitKey(1) & 0xFF == 27) or (cv2.waitKey(1) & 0xFF == ord('q')):
            break
    cap.release()
    cv2.destroyAllWindows()

#####################
# No arguments given
#####################
if not args.file and not args.camera:
    print("At least one parameter is required.")
    parser.print_help()
    exit()

########################
# Tune parameters
########################

#load image
image_path = os.getcwd() + '/first_frame.jpg'
image = cv2.imread(image_path)

# Define initial parameters
initial_block_size = params.block_size
initial_offset = params.offset
initial_min_blob_size = params.min_area  # Minimum blob size in pixels
initial_max_blob_size = params.max_area  # Maximum blob size in pixels
min_blob_size=np.copy(initial_min_blob_size)
max_blob_size=np.copy(initial_max_blob_size)

# Function to process the image based on current parameters
def process_image(block_size, offset):
    # Convert to grayscale
    current_image = image.copy()
    gray = cv2.cvtColor(current_image, cv2.COLOR_BGR2GRAY)
    # Ensure block_size is odd and greater than 1
    block_size = max(3, block_size)  # Ensure minimum value of 3 (an odd number)
    if block_size % 2 == 0:
        block_size += 1  # Ensure block_size is odd
    # Apply adaptive thresholding
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, block_size, offset)
    thresh = cv2.bitwise_not(thresh)
    # Contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # Draw contours and calculate area (number of pixels) per blob
    for contour in contours:
        area = cv2.contourArea(contour)
        if min_blob_size < area < max_blob_size:
            cv2.drawContours(current_image, [contour], -1, (0, 255, 0), 2)
            # Calculate centroid (center) of the contour
            M = cv2.moments(contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                # Display area at the centroid
                cv2.putText(current_image, f'{area}', (cx - 20, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
     # Display the thresholded image
    # ~ cv2.imshow('Thresholded Image', thresh)
    cv2.imshow('Threshold Image', current_image)

# Initialize trackbars window and callback function
cv2.namedWindow('Threshold Parameters')

# Create trackbars for parameter adjustment
cv2.createTrackbar('Block size', 'Threshold Parameters', initial_block_size, 81, lambda x: None)  # Maximum value 81 for odd numbers
cv2.createTrackbar('Offset', 'Threshold Parameters', initial_offset, 50, lambda x: None)
cv2.createTrackbar('Min blob size', 'Threshold Parameters', initial_min_blob_size, 1000, lambda x: None)
cv2.createTrackbar('Max blob size', 'Threshold Parameters', initial_max_blob_size, 1000, lambda x: None)

# Initial processing
process_image(initial_block_size, initial_offset)

# Main loop to update parameters and display image
while True:
    # Check for key press
    key = cv2.waitKey(1) & 0xFF
    # Exit loop on 'q' key press
    if key == ord('q') or key == 27:
        break
    # Get current trackbar positions
    block_size = cv2.getTrackbarPos('Block size', 'Threshold Parameters')
    offset = cv2.getTrackbarPos('Offset', 'Threshold Parameters')
    min_blob_size = cv2.getTrackbarPos('Min blob size', 'Threshold Parameters')
    max_blob_size = cv2.getTrackbarPos('Max blob size', 'Threshold Parameters')
    # Process the image with current parameters
    process_image(block_size, offset)

# Clean up
cv2.destroyAllWindows()

#if block size is not odd, we convert to odd
if block_size % 2 ==0:
    block_size+=1
else:
    pass

print(f" Block size (*should always be odd!): {block_size} \n Offset: {offset} \n Min area: {min_blob_size} \n Max area: {max_blob_size}")

#in case we change some parameter, we update the parameter file, otherwise we do not touch
if block_size!=initial_block_size or offset!=initial_offset or max_blob_size!=initial_max_blob_size or min_blob_size!=initial_min_blob_size:
    #update parameters in params.py
    with open('params.py','r',encoding='utf-8') as file:
        data = file.readlines()    
    data[2]= "block_size = {0}\n".format(block_size)
    data[3]= "offset = {0}\n".format(offset)
    data[10]= "min_area = {0}\n".format(min_blob_size)
    data[11]= "max_area = {0}\n".format(max_blob_size)
    with open('params.py', 'w', encoding='utf-8') as file:
        file.writelines(data)
    #reload parameters in case they were modified
    importlib.reload(params)

########################################################################
########################################################################
########################################################################

########################################################################
#                   Parameter implementation
########################################################################

# colours is a vector of BGR values which are used to identify individuals in the video
# since we only have one individual, the program will only use the first element from this array i.e. (0,0,255) - red
# number of elements in colours should be greater than n_inds (THIS IS NECESSARY FOR VISUALISATION ONLY)
n_inds = params.n_inds
colours = params.colours
mot = params.mot
k_means = params.k_means

# this is the block_size and offset used for adaptive thresholding (block_size should always be odd)
# these values are critical for tracking performance
block_size = params.block_size
offset = params.offset

# the scaling parameter can be used to speed up tracking if video resolution is too high (use value 0-1)
scaling = params.scaling

# minimum area and maximum area occupied by the animal in number of pixels
# this parameter is used to get rid of other objects in view that might be hard to threshold out but are differently sized
min_area = params.min_area
max_area = params.max_area

# name of source video and paths
video = args.name
if args.file:
    input_vidpath = args.file
output_vidpath = './processing_file.mp4'
output_filepath = './processing_file.csv'
codec = 'DIVX' # try other codecs if the default doesn't work ('DIVX', 'avc1', 'XVID') note: this list is non-exhaustive

########################################################################
########################################################################

# The cell below runs the tracking code

# In[3]:

##############
# video file
##############
if args.file:
    print(f"File path: {args.file}")
    # Open the video file
    cap = cv2.VideoCapture(args.file)
    # Check if video opened successfully
    if cap.isOpened() == False:
        sys.exit('Video file cannot be read! Please check input_vidpath to ensure it is correctly pointing to the video file')

##############
# live feed
##############
if args.camera:
    print(f"Camera ID: {args.camera}")
    # ~ cap = cv2.VideoCapture(int(args.camera))
    cap = cv2.VideoCapture(int(args.camera))
    if cap.isOpened() == False:
        sys.exit("Cannot open camera. You can try using v4l2-ctl --list-devices or ls /dev/video* to see available devices")


########################################################################
#                   Start analysing video
########################################################################

## Video writer class to output video with contour and centroid of tracked object(s)
# make sure the frame size matches size of array 'final'
fourcc = cv2.VideoWriter_fourcc(*codec)
output_framesize = (int(cap.read()[1].shape[1]*scaling),int(cap.read()[1].shape[0]*scaling))
out = cv2.VideoWriter(filename = output_vidpath, fourcc = fourcc, fps = 30.0, frameSize = output_framesize, isColor = True)

## Individual location(s) measured in the last and current step
meas_last = list(np.zeros((n_inds,2)))
meas_now = list(np.zeros((n_inds,2)))

last = 0
df = []
#----------------------------------------------------------------------#
#       Check if direction is needed or not
#----------------------------------------------------------------------#
#Direction = minimal distance (in px) for the animal or object to move in order to compute direction. In other words, if the animal doesn't move more than this distance, we take the previous direction.
#This is to avoid computing direction when the animal is still, which can lead to errors. This is only used if the argument is given, otherwise Tracktor will not compute direction.
if args.direction:
    direction = args.direction
    angle = 0 #angle, we start with zero as default
    prev=list(np.zeros((n_inds,2))) #previous position to compute atan2
    temp = pd.DataFrame(columns=['time', 'pos_x', 'pos_y', 'direction', 'id']) # add direction
else:
    temp = pd.DataFrame(columns=['time', 'pos_x', 'pos_y','id']) # without direction
#----------------------------------------------------------------------#

temp.to_csv(output_filepath, sep=',')

if args.track:
    script_path="tracking.ps1"
    process=subprocess.Popen(["powershell", "-ExecutionPolicy", "Bypass", "-File", script_path], shell=True)

t0=time.time() #take start time
while(True):
    # Capture frame-by-frame
    ret, frame = cap.read()
    this = cap.get(1) ######
    if ret == True:
        frame = cv2.resize(frame, None, fx = scaling, fy = scaling, interpolation = cv2.INTER_LINEAR)
        thresh = tr.colour_to_thresh(frame, block_size, offset)
        final, contours, meas_last, meas_now = tr.detect_and_draw_contours(frame, thresh, meas_last, meas_now, min_area, max_area)
        if len(meas_now)==0 or len(meas_last)==0:
            # Display the resulting frame
            out.write(final)
            cv2.imshow('Video', final)
            key=cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                break
            continue
        else:
            # Apply k_means algorithm if k_means = True
            if k_means:
                if len(meas_now) != n_inds:
                    contours, meas_now = tr.apply_k_means(contours, n_inds, meas_now)
            row_ind, col_ind = tr.hungarian_algorithm(meas_last, meas_now)
            final, meas_now, df = tr.reorder_and_draw(final, colours, n_inds, col_ind, meas_now, df, mot, this)
            # Create output dataframe
            for i in range(n_inds):
                if args.direction:
                    Xt=meas_now[i][0]-prev[i][0]
                    Yt=meas_now[i][1]-prev[i][1]
                    # if the distance moved is higher than X pixels we update direction and previous position
                    if np.sqrt(Xt**2 + Yt**2) > int(direction):
                        angle=math.degrees(math.atan2(Yt,Xt)) %360
                        prev[i]=meas_now[i][0:2]
                    # data we save depends on live tracking or video (time vs frame)
                    if args.camera:
                        df.append([time.time()-t0, meas_now[i][0], meas_now[i][1], angle, i])
                    elif args.file:
                        df.append([this, meas_now[i][0], meas_now[i][1], angle, i])
                else:
                    if args.camera:
                        df.append([time.time()-t0, meas_now[i][0], meas_now[i][1],i])
                    elif args.file:
                        df.append([this, meas_now[i][0], meas_now[i][1],i])
            # Write positions to file dynamically
            temp=pd.DataFrame(df[-1:])
            temp.to_csv(output_filepath, mode='a',header=False,index=False)
            # Display the resulting frame
            out.write(final)
            cv2.imshow('Video', final)
            # ~ if cv2.waitKey(1) == 27 or meas_now[0][0] < 20 or meas_now[0][0] > cap.get(3) - 20 or meas_now[0][1] < 20 or meas_now[0][1] > cap.get(4) - 20: # add this line when object detection is required in ALL frames
            key=cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                break
    if args.file:
        if last >= this:
            break
        last = this


#terminate powershell script. If this interferes with other processes running in the computer, comment it and kill the process manually after plots:
#Push Ctrl + C (inside the cmd prompt)
if args.track:
    print("Terminating tracking process...")
    os.system('taskkill /IM powershell.exe /F')

## Write positions to file & add index
if args.direction:
    df = pd.DataFrame(np.matrix(df), columns = ['time','pos_x','pos_y', 'direction', 'id'])
else:
    df = pd.DataFrame(np.matrix(df), columns = ['time','pos_x','pos_y', 'id'])

#For video, change column name
if args.file:
    df.rename(columns={'time':'frame'}, inplace = True)
    print(df)
    df.to_csv(output_filepath, sep=',', index = False)

#For live tracking, add frame column (this is an approximation as we do not control the FPS rate here)

if args.camera:
    df.insert(0,'frame', np.repeat(np.arange(1, (len(df)+1)/n_inds),n_inds))
    df.to_csv(output_filepath, sep=',', index = False)

## When everything done, release the capture
cap.release()
out.release()
cv2.destroyAllWindows()
cv2.waitKey(1)

# In need to plot graphs again but without running the tracker, use the following command:
#df = pd.read_csv(output_filepath)

########################################################################
########################################################################

#Create missing folders, change name and move file
# In[4]:

import matplotlib.pyplot as plt

if os.path.isdir('./imgs'):
    pass
else:
    os.mkdir('imgs')
    
if os.path.isdir('./imgs/{0}'.format(args.name)):
    pass
else:
    os.mkdir('./imgs/{0}'.format(args.name))
    
os.system("move ./processing_file.csv ./imgs/{0}/{0}.csv".format(args.name))
os.system("move ./processing_file.mp4 ./imgs/{0}/{0}.mp4".format(args.name))

##########################################################################
#                       Summary statistics
##########################################################################

# The cells below provide functions to perform basic summary statistics.
# In this case, distance moved between successive frames, cumulative distance, velocity and acceleration.

# In[5]:

# The smoothing window parameter determines the extent of smoothing (this parameter must be odd)
smoothing_window = 5


#1. Inverse Y axis
if ymax >= max(df["pos_y"]):
    df["pos_y"] = ymax - df["pos_y"]
else:
    df["pos_y"] = max(df["pos_y"]) - df["pos_y"]

# 2. Compute velocity and acceleration
dx = df['pos_x'] - df['pos_x'].shift(n_inds)
dy = df['pos_y'] - df['pos_y'].shift(n_inds)
d2x = dx - dx.shift(n_inds)
d2y = dy - dy.shift(n_inds)
df['speed'] = np.sqrt(dx**2 + dy**2)
df['smoothed_speed'] = scipy.signal.savgol_filter(df['speed'], smoothing_window, 1)
df['accn'] = np.sqrt(d2x**2 + d2y**2)
df['smoothed_accn'] = scipy.signal.savgol_filter(df['accn'], smoothing_window, 1)
df.head()

# FIGURE 1 A
# Tracked path
if n_inds==1:
    plt.figure(figsize=(5,5))
    plt.scatter(df['pos_x'], df['pos_y'], c=df['frame'], alpha=0.5)
    plt.xlabel('X', fontsize=16)
    plt.ylabel('Y', fontsize=16)
    plt.tight_layout()
    plt.savefig('imgs/' + args.name + '/fig1a.eps', format='eps', dpi=300)
    plt.show()
else: #for more than 1 individual
    plt.figure(figsize=(5,5))
    plt.scatter(df['pos_x'], df['pos_y'], c=df['id'], cmap= 'jet', alpha=0.5)
    plt.xlabel('X', fontsize=16)
    plt.ylabel('Y', fontsize=16)
    plt.tight_layout()
    plt.savefig('imgs/' + args.name + '/fig1a.eps', format='eps', dpi=300)
    plt.show()

# FIGURE 1 B
# Density plot
plt.figure(figsize=(5,5))
plt.hist2d(df['pos_x'], df['pos_y'], bins=20)
plt.xlabel('X', fontsize=16)
plt.ylabel('Y', fontsize=16)
plt.tight_layout()
plt.savefig('./imgs/' + args.name + '/fig1b.eps', format='eps', dpi=300)
plt.show()


# In[6]:
## Parameters like speed and acceleration can be very noisy. Small noise in positional data is amplified as we take the
## derivative to get speed and acceleration. We therefore smooth this data to obtain reliable values and eliminate noise.

#----------------------------------------------------------------------#
#           Conversion to cm and seconds
#----------------------------------------------------------------------#

# Movement measures are converted from pixels and frames to real-world measures (cms and secs)

# Pixels per cm to in the recorded video to calculate distances
# if resolution and distance in cm was given, it will be used here, otherwise we use standard conversion of px to cm,
# which may not be accurate.

if xdist:
    pxpercm = (xmax/xdist) * scaling
else:
    # ~ pxpercm = 1/0.026 * scaling
    pxpercm = 1 #keep


#Convert px to cm
if args.file:
    df['time'] = df['frame'] * fps
    df['speed'] = df['speed'] * fps / pxpercm
    df['smoothed_speed'] = df['smoothed_speed'] * fps / pxpercm
    df['accn'] = df['accn'] *fps * fps / pxpercm
    df['smoothed_accn'] = df['smoothed_accn'] * fps * fps / pxpercm
    # ~ df['cum_dist'] = df['cum_dist'] / pxpercm -- this is done later
    df.head()
elif args.camera:
    dt = df['time'] - df['time'].shift(n_inds)
    df['speed'] = (df['speed'] / dt) * (1 / pxpercm)
    df['smoothed_speed'] = (df['smoothed_speed'] / dt) * (1 / pxpercm)
    df['accn'] = (df['accn'] /(dt*dt)) * (1 / pxpercm)
    df['smoothed_accn'] = (df['smoothed_accn'] / (dt*dt)) * (1 / pxpercm)
    # ~ df['cum_dist'] = df['cum_dist'] / pxpercm -- this is done later
    df.head()

np.nanmax(df['smoothed_speed']), np.nanmax(df['smoothed_accn'])

# In[7]:

## We now remove any outliers that remain post smoothing
## Here we want to be conservative and not eliminate any relavant points as outliers. We therefore choose a high 'm' value
## in the reject_outliers functions. The best approach is to visually compare smoothed data with the original data

# FIGURE 2 A
unique_ids = df['id'].unique()

plt.figure(figsize=(10, 6))  # Adjust figure size as needed.

for individual_id in unique_ids:
    indiv_data = df.loc[df['id'] == individual_id, ['speed', 'time']].reset_index()
    index = tr.reject_outliers(indiv_data['speed'], m = 6)
    index = np.array(index[0])
    indiv_data=indiv_data.loc[index,]
    indiv_data['cum_dist'] = indiv_data['speed'].cumsum() #no need conversion, because smooth speed is already in cm
    plt.scatter(indiv_data['time'], indiv_data['cum_dist'], s=8, alpha=0.5, label=f'ID {individual_id}')

plt.xlabel('Time (s)')
if xdist:
    plt.ylabel('Cumulative distance (cm)')
else:
    plt.ylabel('Cumulative distance (px)')
plt.legend(title='Individuals', loc='upper right')
plt.tight_layout()
plt.savefig('./imgs/' + args.name + '/fig2a.eps', format='eps', dpi=300)
plt.show()


# FIGURE 2 B
plt.figure(figsize=(10, 6))  # Adjust figure size as needed.

for individual_id in unique_ids:
    indiv_data = df.loc[df['id'] == individual_id, ['smoothed_speed', 'time']].reset_index()
    index = tr.reject_outliers(indiv_data['smoothed_speed'], m = 6)
    index = np.array(index[0])
    indiv_data=indiv_data.loc[index,]
    indiv_data['cum_dist'] = indiv_data['smoothed_speed'].cumsum() #no need conversion, because smooth speed is already in cm
    plt.scatter(indiv_data['time'], indiv_data['cum_dist'], s=8, alpha=0.5, label=f'ID {individual_id}')

plt.xlabel('Time (s)')
if xdist:
    plt.ylabel('Cumulative distance using Savitzky-Golay filter (cm)')
else:
    plt.ylabel('Cumulative distance using Savitzky-Golay filter (px)')
plt.legend(title='Individuals', loc='upper right')
plt.tight_layout()
plt.savefig('./imgs/' + args.name + '/fig2b.eps', format='eps', dpi=300)
plt.show()


# FIGURE 2 C
plt.figure(figsize=(10, 6))  # Adjust figure size as needed.

for individual_id in unique_ids:
    indiv_data = df[df['id'] == individual_id].reset_index()
    index = tr.reject_outliers(indiv_data['smoothed_speed'], m = 6)
    index = np.array(index[0])
    plt.scatter(indiv_data['time'][index], indiv_data['speed'][index], s=5, alpha=0.5, label=f'ID {individual_id}')
    plt.plot(indiv_data['time'][index], indiv_data['smoothed_speed'][index], lw=3)

plt.xlabel('Time')
if xdist:
    plt.ylabel('Speed (cm/s)')
else:
    plt.ylabel('Speed (px/s)')
plt.tight_layout()
plt.legend(title='Individuals', loc='upper right')
plt.savefig('./imgs/' + args.name + '/fig2c.eps', format='eps', dpi=300)
plt.show()


# FIGURE 2 C
plt.figure(figsize=(10, 6))  # Adjust figure size as needed.

for individual_id in unique_ids:
    indiv_data = df[df['id'] == individual_id].reset_index()
    index = tr.reject_outliers(indiv_data['smoothed_speed'], m = 6)
    index = np.array(index[0])
    plt.scatter(indiv_data['time'][index], indiv_data['speed'][index], s=5, alpha=0.5, label=f'ID {individual_id}')
    plt.plot(indiv_data['time'][index], indiv_data['smoothed_speed'][index], lw=3)

plt.xlabel('Time')
if xdist:
    plt.ylabel('Speed (cm/s)')
else:
    plt.ylabel('Speed (px/s)')
plt.tight_layout()
plt.legend(title='Individuals', loc='upper right')
plt.savefig('./imgs/' + args.name + '/fig2c.eps', format='eps', dpi=300)
plt.show()

