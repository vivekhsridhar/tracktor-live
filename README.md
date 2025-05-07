TracktorLive (v0.9-beta)
============

**TracktorLive** is a real-time video tracking and data serving
framework designed for lightweight, scriptable tracking of individual
animals in behavioral experiments. It
provides programmatic hooks for processing and chunking tracked data
on-the-fly, with minimal boilerplate.

The video tracking used in this project emerges from Tracktor::

**Sridhar, V. H., Roche, D. G., & Gingins, S. (2019).**
_Tracktor: Image-based automated tracking of animal movement and behaviour._
Methods in Ecology and Evolution, 10(6), 815–820.
DOI:[10.1111/2041-210X.13166"](https://doi.org/10.1111/2041-210X.13166)

TracktorLive builds on that work, enabling real-time
tracking, memory sharing, and programmatic control for live applications related
to behavior pipelines.

------------------------------------------------------------------------

✨ Features
----------

-   Real-time tracking of 1 or more individuals from real-time camera feed or pre-recorded video
    sources
-   Buffered data sharing via shared memory (suitable for high-speed
    use)
-   Modular "cassette" system for on-the-fly processing
-   Built-in support for:
    -   Data streaming to external clients
    -   Live or on-demand video and data recording
-   A number of useful example scripts and a growing library of server- and
    client-side casettes
-   Minimal external dependencies (NumPy, OpenCV, Scikit-Learn etc.)

------------------------------------------------------------------------

🧠 Concept
---------

TracktorLive works on a **server--client model**, where:

-   A **server** processes a video stream and maintains a shared data
    buffer with clock and tracked locations.
-   One or more **clients** can connect and access this data in real
    time.
-   Small, user-defined functions ("cassettes") can be registered to run
    every frame or at server shutdown.
-   This way, all tracking and multiprocessing happens in the background
    allowing users without computer vision experience to directly get involved
    with such experimental setups.

All interaction is via helper functions like `spawn_trserver`,
`run_trsession`, and decorators like `@server`, `@server.stopfunc`.

------------------------------------------------------------------------

📦 Installation
--------------

TracktorLive is mainly targeted towards Linux-like environments. Windows
users are asked to use Windows Subsystem for Linux (WSL) to use our software.
For running this software on a Linux-like system, you can run

    ```bash
    pip install tracktorlive
    ```

For usage in other platforms, see [DOCS.md](./DOCS.md).

------------------------------------------------------------------------

🔁 Example: Print current location of animal
---------------------------------------------

```python
import tracktorlive as trl

server, semm = trl.spawn_trserver("video.mp4", params, n_ind=1, buffer_size=1, realtime=False)
client = trl.spawn_trclient(server.feed_id)

@client
def printloc(data, clock):
    pos = data[0,:,-1]
    print(clock[-1], ":", pos)
    

run_trsession(server, semm, client)
```

🧪 Real-world Use Cases
----------------------

We provide five complete examples to demonstrate the capabilities of this
software.

- [Visualise](./examples/zzx-visualise): simply track animals and add tracked
  contours and centroids to the video.
- [Arduino-comm](./examples/zx-arduino-comm): trigger an LED to turn on on an
  Arduino board when an animal is within a certain location
- [Looming stimulus](./examples/zy-looming-video): play a brief video (or,
  indeed, run any shell command) when an animal is in movement.
- [Registration](./examples/zzz-registration): save to disk a smaller video with
  the tracked individual at the centre (ideal for later steps including posture
  recognition and so on)
- [Chunking](./examples/zz-video-chunking): record videos only when two
  individuals are interacting with each other.

While these are the uses so far, we encourage users to try more things. We have
discussed as potential future applications, e.g., 3D tracking using 3 cameras,
and camera control to select recording device based on individual's location.


📬 Status
--------

TracktorLive is a still an evolving toolkit. APIs may change. You're
encouraged to adapt parts for your own research or build wrappers that
suit your workflow.

For questions or bugs, feel free to open an issue or reach out directly.
