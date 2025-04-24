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

import config
import memorymanagement as mmg
import paramfixing
import trackutils

ADDR='127.0.0.1'

def _runforever(server):
    cap = trackutils.get_vid(server.vidinput, vidtype=server.vid_source_type)
    t_init = time.time()
    databuffer, clockbuffer = server.setup_shared_arrays()
    while server.running.value and not server.timed_out():
        try:
            server._eachframe(cap, databuffer, clockbuffer)
        except KeyboardInterrupt:
            server.running.value = False
            break
    cap.release()
    #server.stop()#???

class SyncManager(BaseManager): pass

def _make_sem():
    return mp.Semaphore(1)

SyncManager.register('get_semaphore', callable=_make_sem)
port_num = random.choice(range(12000, 20000))
def run_semaphore_server():
    manager = SyncManager(address=(ADDR, port_num), authkey=b'secret')
    s = manager.get_server()
    try:
        s.serve_forever()
    except KeyboardInterrupt:
        s.stop()


def wait_for_server(address, timeout=5.0):
    host, port = address
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except (ConnectionRefusedError, socket.timeout):
            time.sleep(0.1)
    raise RuntimeError(f"Timeout: could not connect to manager at {address}")


class TracktorServer:
    def __init__(self,
                    vidinput,
                    params,
                    n_ind,
                    buffer_size=10,#seconds
                    datfile=None,
                    draw=False,
                    feed_id=None,
                    keep_recordings=False,
                    keep_video=False,
                    port_num=port_num,
                    realtime=True,
                    recfile=None,
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
        self.datfile = datfile
        self.keep_recordings = mp.Value('b', keep_recordings)
        self.keep_video = mp.Value('b', keep_video)
        self.n_ind = n_ind
        self.params = params
        self.port_num = port_num
        self.recfile = recfile
        self.vidinput = vidinput
        self.write_recordings = mp.Value('b', write_recordings)
        self.write_video = mp.Value('b', write_video)

        if timeout is None:
            self.timeout = np.inf
        else:
            self.timeout = timeout
        self.draw = draw

        wait_for_server((ADDR, port_num))
        self.resmanager = mp.Manager()
        self.manager = SyncManager(address=(ADDR, port_num), authkey=b'secret')
        self.manager.connect()

        self.semaphore = self.manager.get_semaphore()
        self.port_num = port_num
        self.serverproc = None

        if not "fps" in params:
#            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            pass
        else:
            self.fps = params["fps"]


        self.datashm, self.clockshm = self.setup_shared_mems()
        self.databuffer, self.clockbuffer = self.setup_shared_arrays()

        self.framesbuffer = [np.nan for i in range(int(self.fps * self.buffer_size))]
        self.framesbuffer = self.resmanager.list(self.framesbuffer)
        self.vid_source_type = "cam"
        if not realtime:
            self.vid_source_type = "file"


        self.create_feed_file()
        self.atstart = {}
        self.casettes = {}
        self.atstop = {}

        self.meas_last = [[0, 0] for j in range(self.n_ind)]
        self.meas_now = [[0, 0] for j in range(self.n_ind)]
        self.meas_last = self.resmanager.list(self.meas_last)
        self.meas_now = self.resmanager.list(self.meas_now)

        self.recorded_frames = self.resmanager.list()
        self.recorded_points = self.resmanager.list()
        self.recorded_times = self.resmanager.list()
        
    def __str__(self):
        return f"{self.__class__.__name__} object feed_id:{self.feed_id}"

    def __repr__(self):
        return f"{self.__class__.__name__} object feed_id:{self.feed_id}"

    def __call__(self, f):
        assert callable(f), f"decorate only functions."
        self.atstart[f.__name__] = f
        return f

    def __call__(self, f):
        assert callable(f), f"decorate only functions."
        self.casettes[f.__name__] = f
        return f

    def __call__(self, f):
        assert callable(f), f"decorate only functions."
        self.atstop[f.__name__] = f
        return f

    def get_feed_filename(self):
        return joinpath(config.FEEDS_DIR, f"tlfeed-{self.feed_id}")

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

    def get_data(self):
        self.semaphore.acquire()
        data = self.databuffer.copy()
        self.semaphore.release()

        return data

    def get_times(self):
        self.semaphore.acquire()
        times = self.clockbuffer.copy()
        self.semaphore.release()

        return times

    def get_clients(self):
        return glob.glob(
                joinpath(config.CLIENTS_DIR,
                            f"tlclient-{self.feed_id}-*"
                        )
                )

    def _eachframe(self, cap, databuffer, clockbuffer):#tracking happens here

        try:
            self.current_frame, frame_index = trackutils.get_frame(cap)
        except EOFError as e:
            if self.vid_source_type == "file":
                # file completed
                self.running.value = False
            else:
                print(f"encountered inexplicable EOFERROR: {e}")
                pass

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
                                    frame_index=frame_index,
                                    draw_circles=self.draw,
                                    use_kmeans=True
                                )

        self.semaphore.acquire()

        databuffer[:,:,:-1] = databuffer[:,:,1:]
        clockbuffer[:-1] = clockbuffer[1:]

        clockbuffer[-1] = time.time() - self.t_init
        databuffer[:,:,-1] = -1.0
        databuffer[:len(self.meas_now[:self.n_ind]),:,-1] = self.meas_now[:self.n_ind]#if you found <= n_ind, fill those up. rest remain -1.0
        self.framesbuffer[:-1] = self.framesbuffer[1:]
        self.framesbuffer[-1] = self.current_frame.copy()

        if self.keep_video:
            if len(self.recorded_frames) == 0:
                self.recorded_frames.extend(self.framesbuffer)
            else:
                self.recorded_frames.append(self.framesbuffer[-1])

        if self.keep_recordings:
            if len(self.recorded_points) == 0:
                self.recorded_points.extend(list(self.databuffer))
                self.recorded_times.extend(list(self.clockbuffer))
            else:
                self.recorded_points.append(self.databuffer[:,:,-1])
                self.recorded_times.append(self.clockbuffer[-1])

        self.semaphore.release()

#    def dumpvideo(self, outfile=None)
#    def dumpdata(self, outfile=None)

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

    def __del__(self):
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

        os.remove(self.get_feed_filename())



if __name__ == "__main__":
#    vidinput = "/home/pranav/Personal/Projects/temp/tracktorlive/Data/vids/fish_video.mp4"
    vidinput = 0
    cap = cv2.VideoCapture(vidinput)

    tune_gui = True
    if tune_gui:
        trackparams = paramfixing.gui_set_params(cap, "cam", write_file=True)
    else:
        with open("params.json") as f:
            trackparams = json.load(f)
    trackparams["fps"] = cap.get(cv2.CAP_PROP_FPS)
    cap.release()

    semmanager = mp.Process(target=run_semaphore_server)
    semmanager.start()
    server = TracktorServer(
                    vidinput=vidinput,
                    params=trackparams,
                    n_ind=1,
                    buffer_size=10,#seconds
                    datfile=None,
                    draw=True,
                    feed_id="trial",
                    keep_recordings=False,
                    keep_video=False,
                    realtime=True,
                    recfile=None,
                    timeout=None,
                    write_recordings=False,
                    write_video=False
                )
    try:
        server.run()

        tnow = time.time()
        while not server.timed_out() and server.running.value:
            time.sleep(0.2)
#        time.sleep(0.01)
    except KeyboardInterrupt:
        print("Stopping everything now")
    finally:
        server.stop()
        del server
        semmanager.terminate()
        semmanager.join()
        semmanager.close()
