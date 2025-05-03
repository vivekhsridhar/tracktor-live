Proximity-Based Video Chunking
==============================

This example demonstrates how to capture short video segments only when
tracked individuals come within a specified distance of each other. It
is useful in scenarios where interactions are rare and continuous
recording would be wasteful.

Purpose
-------

The system monitors position data extracted from video input and
automatically saves short clips to disk when any two individuals are
close together. This allows for real-time filtering and efficient
storage of only behaviorally relevant video.

How It Works
------------

1.  A video is analyzed frame by frame using real-time tracking.
2.  A user-defined function periodically checks the distance between
    individuals.
3.  When the distance falls below a configurable threshold, recording is
    enabled. When they move apart, recording stops and the saved frames
    are written to a file.
4.  At the end of the input (if using video), a final check ensures any
    remaining recording is saved.

Output
------

Chunks are saved into the `ultralisks-chunked/` directory as individual
video files. Each file corresponds to a brief period of close proximity.

Usage
-----

Place your input video (e.g. `ultralisks.mp4`) and tracking parameter
file (e.g. `brood-war-params.json`) in the working directory. Then run:

    python chunker.py

You can adjust the distance threshold and output directory within the
script.

Real-World Applications
-----------------------

- Performing more advanced video analyses on chunks can be faster than the
  alternative
- Great for picking only interactions

# Disclaimer:
This example includes a video excerpt from StarCraft: Brood War (1998), developed and published by Blizzard Entertainment,
used here solely for academic, non-commercial demonstration purposes. All intellectual property rights to StarCraft remain with 
Blizzard Entertainment. No affiliation or endorsement is implied.

The footage is used under fair use provisions for research and educational display of proximity-based video chunking systems.

