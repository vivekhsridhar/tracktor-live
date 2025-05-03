# Pranav Minasandra, Vivek H Sridhar, and Isaac Planas-Sitja
# 14 Apr 2025
# pminasandra.github.io

"""
provides class TracktorServer, for underlying tracking and dataserving needs
"""

import glob
import json
import multiprocessing as mp
import multiprocessing.shared_memory as mpshm
from multiprocessing.managers import BaseManager

import os
from os.path import join as joinpath
import pickle
import random
import socket
import time
import ulid

import cv2
import numpy as np

import tracktorlive
from . import memorymanagement as mmg
from . import paramfixing
from . import sync
from . import trackutils
from . import videoout

ADDR='127.0.0.1'
class SyncManager(BaseManager): pass
SyncManager.register('get_semaphore')


def _runforever(server):
    cap = trackutils.get_vid(server.vidinput)
    t_init = time.time()
    databuffer, clockbuffer = server.setup_shared_arrays()

    for func in server.atstart:
        server.atstart[func](server)
    while server.running.value and not server.timed_out():
        try:
            server._eachframe(cap, databuffer, clockbuffer)
        except KeyboardInterrupt:
            server.running.value = False
            break
        except trackutils.VideoEndedError:
            server.running.value = False
            break

    for func in server.atstop:
        server.atstop[func](server)
    cap.release()
    #server.stop()#???


class TracktorServer:
    def __init__(self,
                    vidinput,
                    params,
                    n_ind,
                    buffer_size=10,#seconds
                    draw=False,
                    feed_id=None,
                    keep_recordings=False,
                    keep_video=False,
                    port_num=281197,
                    realtime=True,
                    timeout=None,
                    write_recordings=False,
                    write_video=False
                ):
        """
        bla bla bla
        """

        if not feed_id:
            self.feed_id = str(ulid.ULID())
        else:
            self.feed_id = feed_id
        self.buffer_size = buffer_size
        self.keep_recordings = mp.Value('b', keep_recordings)
        self.keep_video = mp.Value('b', keep_video)
        self.n_ind = n_ind
        self.params = params
        self.port_num = port_num
        self.vidinput = vidinput
        self.write_recordings = mp.Value('b', write_recordings)
        self.write_video = mp.Value('b', write_video)

        if timeout is None:
            self.timeout = np.inf
        else:
            self.timeout = timeout
        self.draw = draw

        sync.wait_for_server((ADDR, port_num))
        self.manager = SyncManager(address=(ADDR, port_num), authkey=b'secret')
        self.manager.connect()
        self.semaphore = self.manager.get_semaphore(self.feed_id)

        self.port_num = port_num
        self.serverproc = None

        if "fps" in params:
            self.fps = params["fps"]

        self.datashm, self.clockshm = self.setup_shared_mems()
        self.databuffer, self.clockbuffer = self.setup_shared_arrays()

        self.resmanager = mp.Manager()
        self.framesbuffer = [None for i in range(int(self.fps * self.buffer_size))]
        self.vid_source_type = "cam"
        if not realtime:
            self.vid_source_type = "file"

        self.create_feed_file()
        self.atstart = {}
        self.casettes = {}
        self.atstop = {}

        self.meas_last = [[0, 0] for j in range(self.n_ind)]
        self.meas_now = [[0, 0] for j in range(self.n_ind)]
#        self.meas_last = self.resmanager.list(self.meas_last)
#        self.meas_now = self.resmanager.list(self.meas_now)

        self.recorded_frames = [] 
        self.recorded_points = [] 
        self.recorded_times  = [] 
        cap_temp = cv2.VideoCapture(self.vidinput)
        ret, frame = cap_temp.read()
        self.framesize = (int(frame.shape[1]*1.0),
                            int(frame.shape[0]*1.0))# FIXME: scaling

        if self.write_video.value:
            os.makedirs(self.feed_id, exist_ok=True)
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            self.vidout = cv2.VideoWriter(
                                    filename=joinpath(self.feed_id, str(ulid.ULID())+'.avi'),
                                    fourcc = fourcc,
                                    fps = cap_temp.get(cv2.CAP_PROP_FPS),
                                    frameSize = self.framesize,
                                    isColor = True
                                )
        cap_temp.release()

        if self.write_recordings.value:
            os.makedirs(self.feed_id, exist_ok=True)
            fname = str(ulid.ULID())+'.csv'
            fname = joinpath(self.feed_id, fname)
            self.recout = open(fname, 'w')
            cols = ['time']
            for i in range(self.n_ind):
                cols.extend([f"x{i}", f"y{i}"])
            print(",".join(cols), file=self.recout,flush=True)

    def __str__(self):
        return f"{self.__class__.__name__} object feed_id:{self.feed_id}"

    def __repr__(self):
        return f"{self.__class__.__name__} object feed_id:{self.feed_id}"

    def startfunc(self, f):
        assert callable(f), f"decorate only functions."
        self.atstart[f.__name__] = f
        return f

    def __call__(self, f):
        assert callable(f), f"decorate only functions."
        self.casettes[f.__name__] = f
        return f

    def stopfunc(self, f):
        assert callable(f), f"decorate only functions."
        self.atstop[f.__name__] = f
        return f

    def get_feed_filename(self):
        return joinpath(tracktorlive.FEEDS_DIR, f"tlfeed-{self.feed_id}")

    def create_feed_file(self):
        feeddata = {
            "feed_id":      self.feed_id,
            "fps":          self.fps,
            "buffer_size":  self.buffer_size,
            "n_ind":        self.n_ind,
            "datashm":      self.datashm.name,
            "clockshm":     self.clockshm.name,
            "port_num":      self.port_num,
            "vid_source":   self.vid_source_type,
            "params":       self.params
            }

        feedfile = self.get_feed_filename()
        with open(feedfile, "wb") as feedfile:
            pickle.dump(feeddata, feedfile)

    def setup_shared_mems(self):
        floatsize = np.dtype(np.float64).itemsize
        trackingdatashape = (self.n_ind, 2, int(self.fps*self.buffer_size))
        timedatashape = (int(self.fps*self.buffer_size), )
        trackingdatasize = np.prod(trackingdatashape)* floatsize #size in bytes of 1st shm
        timedatasize = np.prod(timedatashape)*floatsize # size of 2nd shm

        datashm = mmg.create_shared_data(trackingdatasize)
        clockshm = mmg.create_shared_data(timedatasize)

        return datashm, clockshm

    def setup_shared_arrays(self):
        trackingdatashape = (self.n_ind, 2, int(self.fps*self.buffer_size))
        timedatashape = (int(self.fps*self.buffer_size), )
        databuffer = np.ndarray(trackingdatashape,
                           dtype=np.float64,
                           buffer=self.datashm.buf
                       )
        clockbuffer = np.ndarray(timedatashape,
                           dtype=np.float64,
                           buffer=self.clockshm.buf
                       )

        databuffer[:,:,:] = np.nan
        clockbuffer[:] = np.nan

        return databuffer, clockbuffer

    def get_data_and_clock(self):
        self.semaphore.acquire()
        data = self.databuffer.copy()
        clock = self.clockbuffer.copy()
        self.semaphore.release()

        return data, clock

    def get_clients(self):
        return glob.glob(
                joinpath(tracktorlive.CLIENTS_DIR,
                            f"tlclient-{self.feed_id}-*"
                        )
                )

    def _eachframe(self, cap, databuffer, clockbuffer):#tracking happens here

        try:
            self.current_frame, self.frame_index = trackutils.get_frame(cap)
        except trackutils.VideoEndedError as e:
            if self.vid_source_type == "file":
                # file completed
                self.running.value = False
                return None
            else:
                print(f"encountered inexplicable EOFERROR: {e}")
                pass

        for func in self.casettes:
            self.casettes[func](self)

        self.current_frame, contours,\
            self.meas_last, self.meas_now = trackutils.get_contours(
                                            frame=self.current_frame,
                                            meas_last=self.meas_last,
                                            meas_now=self.meas_now,
                                            scaling=1.0,#FIXME
                                            draw_contours=self.draw,
                                            **self.params
                                        )

        self.current_frame, self.meas_now = trackutils.cleanup_centroids(
                                    self.current_frame,
                                    contours,
                                    n_inds=self.n_ind,
                                    meas_last=self.meas_last,
                                    meas_now=self.meas_now,
                                    mot=True,#FIXME
                                    frame_index=self.frame_index,
                                    draw_circles=self.draw,
                                    use_kmeans=True
                                )

        self.semaphore.acquire()

        databuffer[:,:,:-1] = databuffer[:,:,1:]
        clockbuffer[:-1] = clockbuffer[1:]

        if self.vid_source_type == "cam":
            clockbuffer[-1] = time.time() - self.t_init
        else:
            clockbuffer[-1] = self.frame_index/self.fps

        databuffer[:,:,-1] = -1.0
        if len(self.meas_now) > 0:
            databuffer[:len(self.meas_now[:self.n_ind]),:,-1] = self.meas_now[:self.n_ind]#if you found <= n_ind, fill those up. rest remain -1.0
        self.framesbuffer[:-1] = self.framesbuffer[1:]
        self.framesbuffer[-1] = self.current_frame.copy()

        if self.keep_video.value:
            if len(self.recorded_frames) == 0:
                self.recorded_frames.extend([fr for fr in self.framesbuffer if fr is not None])
            else:
                self.recorded_frames.append(self.current_frame)

        if self.keep_recordings.value:
            if len(self.recorded_points) == 0:
                self.recorded_points.extend(list(self.databuffer))
                self.recorded_times.extend(list(self.clockbuffer))
            else:
                self.recorded_points.append(self.databuffer[:,:,-1])
                self.recorded_times.append(self.clockbuffer[-1])


        if self.write_video.value:
            self.vidout.write(self.current_frame)

        if self.write_recordings.value:
            entry=[clockbuffer[-1]]
            entry.extend(list(databuffer.copy()[:,:,-1].reshape(2*self.n_ind)))
            entry=[str(x) for x in entry]
            print(",".join(entry), file=self.recout, flush=True)
        self.semaphore.release()

    def dumpvideo(self, outfile=None):
        if outfile is not None:
            self.semaphore.acquire()
            frcopy = self.recorded_frames.copy()
            self.semaphore.release()

            videoout.prl_vidout(frcopy, outfile, self.fps, self.framesize)

        self.recorded_frames = []

#    def dumpdata(self, outfile=None):#FIXME

    def run(self):
        self.t_init = time.time()
        self.running = mp.Value('b', True)
        self.serverproc = mp.Process(target=_runforever, args=(self,))
        self.serverproc.start()

    def timed_out(self):
        return time.time() - self.t_init > self.timeout

    def stop(self):
        self.running.value = False
        #self.serverproc.terminate()
        self.serverproc.join()
        self.serverproc.close()
        self.databuffer[:,:,1:] = self.databuffer[:,:,:-1]
        self.clockbuffer[1:] = self.clockbuffer[:-1]

        self.databuffer[:,:,-1] = -1.0
        self.clockbuffer[-1] = -1.0
        if self.write_video.value:
            self.vidout.release()
        if self.write_recordings.value:
            self.recout.close()

    def __del__(self):
        os.remove(self.get_feed_filename())
        if self.running.value:
            self.stop()
            time.sleep(0.001)
        self.datashm.close()
        self.clockshm.close()

        t_close = time.time()
        while len(self.get_clients()) > 0 and time.time() - t_close < 5.0:
            time.sleep(0.01)
            pass
        try:
            self.datashm.unlink()
            self.clockshm.unlink()
        except FileNotFoundError:
            pass
        except KeyError as e:
            print("An inexplicable, commonly occuring error occured upon server closure. ERR001")


def spawn_trserver(vidinput, params, n_ind=1, **kwargs):
    port_num = random.choice(range(12000, 20000))
    semm = sync.prl_sem_server(port_num)
    server = TracktorServer(
                    vidinput=vidinput,
                    params=params,
                    n_ind=n_ind,
                    port_num=port_num,
                    **kwargs
                )
    return server, semm

def close_trserver(server, semm):
    server.stop()
    semm.terminate()
    semm.join()
    semm.close()

def run_trserver(server, semm):
    server.run()

def wait_and_close_trserver(server, semm):
    try:
        while not server.timed_out() and server.running.value:
            time.sleep(0.002)

    except KeyboardInterrupt:
        print(f"Terminating server: {server.feed_id}")
    finally:
        close_trserver(server, semm)


if __name__ == "__main__":
    mp.set_start_method('fork')

    video_directory = "/Users/vivekhsridhar/Library/Mobile Documents/com~apple~CloudDocs/Documents/Code/Python/OpenCV/tracktor"

    vidinput = joinpath(video_directory, "videos", "fish_video.mp4")
#    vidinput = 0
    cap = cv2.VideoCapture(vidinput)

    tune_gui = False
    if tune_gui:
        trackparams = paramfixing.gui_set_params(cap, "file", write_file=True)
    else:
        with open("params.json") as f:
            trackparams = json.load(f)
    trackparams["fps"] = cap.get(cv2.CAP_PROP_FPS)
    cap.release()

    server, semm = spawn_trserver(vidinput, trackparams,
                            n_ind=2, realtime=False, draw=True,
                            feed_id="trial")

    run_trserver(server, semm)
    wait_and_close_trserver(server, semm)
    del server
