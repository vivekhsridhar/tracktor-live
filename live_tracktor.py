#!/usr/bin/env python
# coding: utf-8

# In[1]:
import numpy as np
import pandas as pd
import tracktor as tr
import cv2
import sys
import scipy.signal
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist
import time
import argparse
import os
#get parameters from the params.py file
import params
import importlib

# ## Global parameters
# This cell (below) enlists user-defined parameters

# In[2]:

parser = argparse.ArgumentParser(description='Introduce parameters.')
parser.add_argument('-n', '--name', required=True, help='Name of new video file after analysis')
parser.add_argument('-c', '--camera', required=False, help='Camera device number')
parser.add_argument('-f', '--file', required=False, help='Complete file path')
    
args = parser.parse_args()

########################################################################
#            Tune parameters
########################################################################

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

# mot determines whether the tracker is being used in noisy conditions to track a single object or for multi-object
# using this will enable k-means clustering to force n_inds number of animals
mot = False

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
temp = pd.DataFrame(columns=['frame', 'pos_x', 'pos_y'])
temp.to_csv(output_filepath, sep=',')

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
            row_ind, col_ind = tr.hungarian_algorithm(meas_last, meas_now)
            final, meas_now, df = tr.reorder_and_draw(final, colours, n_inds, col_ind, meas_now, df, mot, this)
            # Create output dataframe
            for i in range(n_inds):
                # ~ df.append([this, meas_now[i][0], meas_now[i][1]]) #########
                df.append([time.time()-t0, meas_now[i][0], meas_now[i][1]])
            ## Write positions to file dynamically
            temp=pd.DataFrame(df[-1:])
            temp.to_csv(output_filepath, mode='a',header=False)
            # Display the resulting frame
            out.write(final)
            cv2.imshow('Video', final)
            # ~ if cv2.waitKey(1) == 27 or meas_now[0][0] < 20 or meas_now[0][0] > cap.get(3) - 20 or meas_now[0][1] < 20 or meas_now[0][1] > cap.get(4) - 20:
            key=cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                break
    if args.file:
        if last >= this:
            break
        last = this ############

## Write positions to file - if we need index, otherwise skip
df = pd.DataFrame(np.matrix(df), columns = ['frame','pos_x','pos_y'])
df.to_csv(output_filepath, sep=',')


## When everything done, release the capture
cap.release()
out.release()
cv2.destroyAllWindows()
cv2.waitKey(1)

df = pd.read_csv(output_filepath)

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
    
os.system("mv ./processing_file.csv ./imgs/{0}/{0}.csv".format(args.name))
os.system("mv ./processing_file.mp4 ./imgs/{0}/{0}.mp4".format(args.name))

# ## Summary statistics
# The cells below provide functions to perform basic summary statistics - in this case, distance moved between successive frames, cumulative distance within a time-window, velocity and acceleration.
# In[5]:

plt.figure(figsize=(5,5))
plt.scatter(df['pos_x'], df['pos_y'], c=df['frame'], alpha=0.5)
plt.xlabel('X', fontsize=16)
plt.ylabel('Y', fontsize=16)
plt.tight_layout()
plt.savefig('imgs/' + args.name + '/ex1_fig1a.eps', format='eps', dpi=300)
plt.show()

plt.figure(figsize=(5,5))
plt.hist2d(df['pos_x'], df['pos_y'], bins=20)
plt.xlabel('X', fontsize=16)
plt.ylabel('Y', fontsize=16)
plt.tight_layout()
plt.savefig('./imgs/' + args.name + '/ex1_fig1b.eps', format='eps', dpi=300)
plt.show()


# In[6]:


## Parameters like speed and acceleration can be very noisy. Small noise in positional data is amplified as we take the
## derivative to get speed and acceleration. We therefore smooth this data to obtain reliable values and eliminate noise.

# the smoothing window parameter determines the extent of smoothing (this parameter must be odd)
smoothing_window = 11

## Fill in the parameters below if you'd like movement measures to be converted from pixels and frames to 
## real-world measures (cms and secs)

# Frame-rate (fps or frames per second) of recorded video to calculate time
# ~ fps = 1000

# Pixels per cm to in the recorded video to calculate distances
pxpercm = 78 * scaling


# In[7]:


dx = df['pos_x'] - df['pos_x'].shift(n_inds)
dy = df['pos_y'] - df['pos_y'].shift(n_inds)
d2x = dx - dx.shift(1)
d2y = dy - dy.shift(1)
df['speed'] = np.sqrt(dx**2 + dy**2)
df['smoothed_speed'] = scipy.signal.savgol_filter(df['speed'], smoothing_window, 1)
df['accn'] = np.sqrt(d2x**2 + d2y**2)
df['smoothed_accn'] = scipy.signal.savgol_filter(df['accn'], smoothing_window, 1)
df['cum_dist'] = df['smoothed_speed'].cumsum()
df.head()


# In[8]:


def cumul_dist(start_fr, end_fr):
    if start_fr != 1:
        cumul_dist = df['cum_dist'][df['frame'] == end_fr].values[0] - df['cum_dist'][df['frame'] == start_fr].values[0]
    else:
        cumul_dist = df['cum_dist'][df['frame'] == end_fr].values[0]
    return cumul_dist


# In[9]:


# ~ cumul_dist(150,200)


# In[10]:


df['time'] = df['frame']
df['speed'] = df['speed']/ pxpercm
df['smoothed_speed'] = df['smoothed_speed']/ pxpercm
df['accn'] = df['accn']/ pxpercm
df['smoothed_accn'] = df['smoothed_accn']/ pxpercm
df['cum_dist'] = df['cum_dist'] / pxpercm
df.head()


# In[11]:


# ~ cumul_dist(140,170) / pxpercm


# In[12]:


np.nanmax(df['smoothed_speed']), np.nanmax(df['smoothed_accn'])


# In[13]:


## We now remove any outliers that remain post smoothing
## Here we want to conservative and not eliminate any relavant points as outliers. We therefore choose a high 'm' value
## in the reject_outliers functions. The best approach is to visually compare smoothed data with the original data
index = tr.reject_outliers(df['smoothed_speed'], m = 6)
index = np.array(index[0])


# In[16]:


plt.scatter(df['time'][index], df['cum_dist'][index], c='#FF7F50', s=8, alpha=0.5)
plt.xlabel('Time (s)')
plt.ylabel('Cumulative distance (cm)')
plt.tight_layout()
plt.savefig('./imgs/' + args.name + '/ex1_fig2a.eps', format='eps', dpi=300)
plt.show()

plt.scatter(df['time'][index], df['speed'][index], s=5, alpha=0.5)
plt.plot(df['time'][index], df['smoothed_speed'][index], c='#FF7F50', lw=3)
# ~ plt.ylim(0,200)
plt.xlabel('Time')
plt.ylabel('Speed (cm/s)')
plt.tight_layout()
plt.savefig('./imgs/' + args.name + '/ex1_fig2b.eps', format='eps', dpi=300)
plt.show()

plt.scatter(df['time'][index], df['accn'][index], s=5, alpha=0.5)
plt.plot(df['time'][index], df['smoothed_accn'][index], c='#FF7F50', lw=3)
# ~ plt.ylim(0,200000)
plt.xlabel('Time')
plt.ylabel('Acceleration (cm/sq.s)')
plt.tight_layout()
plt.savefig('./imgs/' + args.name + '/ex1_fig2c.eps', format='eps', dpi=300)
plt.show()


# In[ ]:




