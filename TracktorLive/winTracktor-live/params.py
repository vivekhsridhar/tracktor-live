# PLEASE DO NOT MODIFY NAMES, ADD OR REMOVE LINES. IF SO, THE MAIN SCRIPT WILL NOT WORK.
# this is the block_size and offset used for adaptive thresholding (block_size should always be odd), these values are critical for tracking performance
block_size = 51
offset = 17

# the scaling parameter can be used to speed up tracking if video resolution is too high (use value 0-1)
scaling = 1.0

# minimum area and maximum area occupied by the animal in number of pixels
# this parameter is used to get rid of other objects in view that might be hard to threshold out but are differently sized
min_area = 116
max_area = 963

# colours is a vector of BGR values which are used to identify individuals in the video
# since we only have one individual, the program will only use the first element from this array i.e. (0,0,255) - red
# number of elements in colours should be greater than n_inds (THIS IS NECESSARY FOR VISUALISATION ONLY)
n_inds = 1
colours = [(0,0,255),(0,255,255),(255,0,255),(255,255,255),(255,255,0),(255,0,0),(0,255,0),(0,0,0)]

#Video parameters for converting the final plots to cm, vid_res = resolution of the video or camera; vid_dist = the real distance in cm covered by the video (x axis)
vid_res = [1920, 1080]
vid_dist = 50

# mot determines whether the tracker is being used in noisy conditions to track a single object or for multi-object
# using this will enable k-means clustering to force n_inds number of animals
mot = False

# k_means determines whether te tracker clustering algorithm to separate merged contours.
# The algorithm is applied when detected contours are fewer than expected objects(number of animals) in the scene.
k_means = False
