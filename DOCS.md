# Documentation for TracktorLive 0.9.0-beta

## Overview

TracktorLive is a lightweight, real-time tracking and data streaming framework
designed for use in behavioural experiments, multi-agent video analysis, and
low-latency response delivery. It builds on the original Tracktor tracking
approach by extending it into a modular, scriptable architecture that supports
real-time computation and flexible output control.

At its core, TracktorLive:

-    Tracks one or more individuals from a live camera or video file

-   Maintains a buffer of recent tracking data in shared memory

-    Serves data to external clients over a simple shared-memory
    interface

-    Allows user-defined functions to process or respond to this data
    frame-by-frame, including modification of server parameters for advanced
    users.

The system is designed to be highly adaptable: we provide examples where you can 
send a message to get stimulus delivery on an Arduino, 
trigger recordings based
on spatial locations of individuals, extract centred video segments, write
custom log files, or launch other local processes.

You can use TracktorLive entirely through helper functions and decorators
without worrying about the internals of the multiprocessing and tracking setup.
The end-user can rely on the TracktorLive internals for all that.

## Quickstart

This section walks you through running your first TracktorLive script using
a video file as input and tracking a single individual.

You’ll need:

-    A video file with reasonably clear contrast (e.g. top-down fish or insect
    footage). Tracktor's adaptive thresholding makes it reasonably resilient to
    background disturbances especially when tracking one individual.

-    A parameter JSON file defining thresholds and filters for tracking (see
    example below for how to generate one)

```python
import json
import time
import numpy as np
import tracktorlive as trl

# Load tracking parameters
with open("params.json") as f:
    params = json.load(f)
params["fps"] = 30.0

# Start a server to track one individual
server, semm = trl.spawn_trserver("video.mp4", params, n_ind=1, realtime=False)

# Start a client for real-time access to tracking data
client = trl.spawn_trclient(feed_id=server.feed_id)

# Define what the client should do each polling cycle
@client
def print_coords(data, clock):
    coords = data[0, :, -1] #the latest coordinates of the individual
    t = clock[-1] # latest timestamp
    if np.all(coords >= 0):
        print(f"t = {t:.2f}s, x = {coords[0]:.1f}, y = {coords[1]:.1f}")

# Run server and client together
trl.run_trsession(server, semm, client)

```

### Note on Data Shapes

The function `server.get_data_and_clock()` returns two NumPy arrays:

    data: shape (n_ind, 2, buffer_length)

    clock: shape (buffer_length,)

This means:

-    For 1 individual and a 10-second buffer at 30 fps, data.shape will be (1, 2, 300)

-    The most recent positions are always at `data[:, :, -1]`

-    The clock array holds the corresponding timestamps, latest at `clock[-1]`

These shapes are explained in detail in the [Core Concepts] section.


## Installation

TracktorLive will soon be installable via pip and brings in all Python
dependencies automatically. However, you’ll need some basic system tools (like
compilers and build tools) installed to support underlying libraries such as
OpenCV.

Below are platform-specific setup instructions.

### 🐧 Linux (Debian/Ubuntu)

1. Update and upgrade system packages

    ```bash
    sudo apt update
    sudo apt upgrade -y
    ```

2. Install development tools

    ```bash
    sudo apt install -y build-essential cmake make flex bison lld python3-dev
    ```

3. Ensure Python and pip are available

    ```bash
    sudo apt install -y python3 python3-pip python3-setuptools python3-wheel
    ```

4. Install Tracktorlive

    ```bash
    python -m pip install tracktorlive
    ```

(you might need to use `python3` instead of `python` based on your installation.

### 🍎 macOS

1. Install Homebrew (if not already installed):

    ```bash 
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    ```

2. Install system tools and python

    ```bash 
    brew install cmake make flex bison lld
    brew install python
    ```

3. Install TracktorLive

    ```bash
    pip3 install tracktorlive
    ```


### 🪟 Windows (via WSL)

> TracktorLive is designed for Linux-like environments. Windows users should
> install WSL (Windows Subsystem for Linux, see below).

1. Install WSL (Windows 10 and 11 only). Open the pre-installed software
   'Powershell', and run:

    ```powershell
    wsl --install -d Ubuntu
    ```

    You might be prompted to enter a username and password for the virtual Linux
    system, which you will need to remember.
    Restart your computer after this step finishes.

2. After restarting, start WSL on Powershell

    ```powershell
    wsl
    ```

3. You are now within WSL in a 'bash' shell. Run

    ```bash
    cd ~
    ```

    to enter your Linux home directory.

4. To get access to GUI functionality on WSL, e.g., for fixing parameter values,
    run the following commands within WSL.

    ```bash
    sudo apt install vlc
    sudo apt install python3-pyqt5 python3-opencv libxcb-xinerama0
    ```

    **Note**: The GUI might not work on outdated versions of WSL.

5. Follow Linux instructions (above) for further proceedings.

6. Run all TracktorLive scripts within WSL.

## CLI usage

The command `tracktorlive` becomes available on your shell as soon as you
install our library. `tracktorlive -h` shows you a list of options. 

1. **Getting param values:** The first
thing you can do with the program is get the parameters needed for tracking with
your camera or pre-recorded video. For instance, if you have a single camera
connected, in your terminal, you can use:

    ```bash
    tracktorlive gui --camera 0
    ```

    To get parameters from a pre-recorded video, use:

    ```bash
    tracktorlive gui --file /path/to/file
    ```

    The `tracktorlive gui` command also has an `--output /path/to/outfile.json`
    argument, by which you can directly store the output of the GUI parameter fixing
    method into a .json file. These files are important for launching servers.

2. **Launching simple servers:** The `tracktorlive` command can also launch
   naive servers without any casettes. This can be done as follows:

   ```bash
   tracktorlive track --camera 0 /path/to/params.json
   ```

    As before, `--file /path/to/file` can be used in place of `--camera 0`.
    Furthermore, the `tracktorlive track` subcommand can optionally take
    a `--feed-id <a-unique-identifier>` and `--numtrack <how-many-individuals>` arguments to
    customise tracking. The server's feed is displayed, and can be used in any
    client-program you wish to write.


## Core concepts


TracktorLive is designed to be minimal and scriptable. Most of the work happens through small user-defined functions called **cassette functions**, which let you control what happens during tracking and what gets saved or triggered.

Cassette functions come in three types:


### 🎬 Client Cassette Functions (Basic)

Client cassette functions are the simplest and most common way to interact with tracking data. They run continuously in the background and receive the latest buffer of tracking data and timestamps. You can use them to trigger devices, monitor zones, save values, or drive visualizations.

A typical client cassette looks like this:

```python
@client
def log_position(data, clock):
    coords = data[0, :, -1]  # x, y of the most recent frame
    print(f"t = {clock[-1]:.2f}s, x = {coords[0]:.1f}, y = {coords[1]:.1f}")
```

This function is automatically called every few milliseconds as long as the tracking is active.
There is no guarantee that the server will have processed another frame by this
time, so the client might get the same data over several iterations. Being
robust to this effect is necessary for real-time applications.

To write one:

* Decorate a function with `@client`
* Accept two arguments: `data` and `clock`
* Use the last index `-1` to access the most recent tracked values
* Optional: use previous time points by indexing further back (e.g. `-2`, `-3`)


### 🧩 Server Cassette Functions

Server cassette functions are slightly more advanced and give you direct access to video frames and state. These are used when you need to:

- Edit video and tracking properties
* Dynamically write video
* Overlay graphics on live frames
* Run tracking-dependent logic directly during processing
- Modify frames prior to processing

```python
@server
def overlay_rectangle(server):
    frame = server.framesbuffer[-1]
    # Draw semi-transparent overlays or annotate frame
```

To write one:

* Decorate a function with `@server`
* Accept a single `server` argument
* Access `server.framesbuffer[-1]` for the latest *tracked* frame
- Access server.current_frame for the frame about to be submitted to the
  tracking procedure
* Access `server.get_data_and_clock()` for safely retrieving position data
* Can modify flags like `server.keep_video.value = True`

---

### ⏹ Stop Cassette Functions

These are called once at the end of a tracking session. They're useful for saving final results like:

* Writing out a video clip
* Saving a CSV file
* Closing resources (e.g., files, serial ports)

```python
@server.stopfunc
def save_final_video(server):
    server.dumpvideo("final.avi") #works only if the server was recording!
```

---

### ⏱ Start Cassette Functions

Start cassettes run once, just before tracking begins. You can use them to sync timers, or log a start event.

```python
@server.startfunc
def announce(server):
    print("Tracking has started.")
```

---

### Internals (Briefly)

Behind the scenes:

* All tracking and cassette execution is multiprocessing-safe
* A shared data buffer and clock are synchronized using a semaphore server
* You don't need to manage threads, timers, or shared memory manually

All you have to do is define functions, decorate them, and run `trl.run_trsession(...)`.

---

## Writing Your Own Cassette Functions

Cassette functions are the core way to use and customize TracktorLive. 
TracktorLive provides flexibility: you can write simple one-liners or build complete pipelines to 
control recordings, trigger devices, or annotate frames.

---

### Writing a Client Cassette (Recommended)

Client cassettes are the easiest place to start. They are regular Python functions that are called automatically every few milliseconds while tracking is active.

To write one:

1. Spawn a client:

   ```python
   feed_id="your-id-here"
   server = trl.spawn_trserver(0, params, realtime=True) # records from camera.
   # Ensure params is a defined dictionary.

   client = trl.spawn_trclient(feed_id)
   ```

2. Decorate your function with `@client`:

   ```python
   @client
   def print_speed(data, clock):
       curr = data[0, :, -1]
       prev = data[0, :, -2]
       dt = clock[-1] - clock[-2]
       if dt > 0:
           speed = np.linalg.norm(curr - prev) / dt
           print(f"{clock[-1]:.2f}s: speed = {speed:.2f}")
   ```

3. Pass the client to `trl.run_trsession(server, semm, client)`

**Notes**:

* `data` has shape `(n_ind, 2, N)`
* Always check for `np.any(data < 0)` to avoid using invalid frames, where
  tracking couldn't find an individual.
- You can also use np.any(np.isnan(data)) to avoid untracked times. (At
  initialisation, the buffer is full of NaNs. These get overwritten as tracking
  proceeds.)


### 🎥 Writing a Server Cassette (Advanced)

If you need access to live frames or want to influence recording directly, you can write a server-side cassette.

Here is an example to begin recording only when the individual moves to the very
left of the screen.

1. Decorate your function with `@server`:


   ```python

   @server
   def monitor(server):
       data, clock = server.get_data_and_clock()
       coords = data[0, :, -1]
       if coords[0] < 100:
           server.keep_video.value = True

   @server.stopfunc
   def end(server):
       server.dumpvideo(outfile="vidout.mp4")
   ```

2. Inside your function:

   - Access current frame about to be tracked with server.current_frame.
   * Access tracked frames with `server.framesbuffer` (list, None when not yet
     tracked)
   * Access tracking data with `server.get_data_and_clock()`
   * Set flags like `keep_video.value`, `write_video.value`, etc.


### ✅ General Advice

* Keep cassette functions short and predictable
* Avoid blocking operations or long sleeps
* Use NumPy and indexing efficiently


## Learning more

TracktorLive includes a set of example scripts that demonstrate common use cases.
These are a great starting point if you're not sure how to structure your logic.

You'll find them in the [`examples/`](./examples/) folder on our GitHub repository.
