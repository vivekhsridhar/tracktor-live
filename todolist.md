# Current to-do list

- [x] Server registers 3 semaphores for time, tracks, and videos
- [x] Server implements 3 shared memories for each above
- [?] (for now, the video sharing is optional)
- [x] Server-side casette
- [x] Client `get_data` and `get_frames` methods
- [x] Client-side usage of 1 semaphores and 3 SHMs
- [x] Validate `trackutils.py`
- [x] wrapper functions for spawning servers and clients
- [x] dumpvideo methods for TracktorServer objects
- [ ] dumpdata methods for TracktorServer objects
- [x] Write `recorder.py` `chunker.py` and `startler.py` in examples directory
- [ ] automatic detection of "file" vs "cam" and fps, and set server.realtime
  automatically.
- [ ] output file names based on the input filenames, and other global params
  brought to beginning + example cleaup
- [x] paramfixing.py: write_file change from bool to str, and if it is None,
  sensibly get a new name.
- [ ] video file-format and codec handling in write_video and dumpvideo
- [x] handle invert variable value (defaults to 51)
- [x] paramfixing using trackutils instead of cv2 functions
