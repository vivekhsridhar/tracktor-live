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
import uuid

import cv2
import numpy as np

import config
import memorymanagement as mmg
import paramfixing
import trackutils


def _runforever(server):
    t_init = time.time()
    databuffer, clockbuffer = server.setup_shared_arrays()
    while server.running.value and not server.timed_out():
        print("exec one _runforever")
        try:
            server._eachframe(databuffer, clockbuffer)
        except KeyboardInterrupt:
            server.running.value = False
            break
    #server.stop()#???

class SyncManager(BaseManager): pass

def _make_sem():
    return mp.Semaphore(1)

SyncManager.register('get_semaphore', callable=_make_sem)
port_num = random.choice(range(12000, 20000))
def run_semaphore_server():
    manager = SyncManager(address=('127.0.0.1', port_num), authkey=b'secret')
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
                    cap,
                    params,
                    n_ind,
                    buffer_size=10,#seconds
                    realtime=True,
                    feed_id=None,
                    keep_recordings=False,
                    keep_video=False,
                    write_recordings=False,
                    write_video=False,
                    recfile=None,
                    datfile=None,
                    addr='127.0.0.1',
                    port_num=port_num,
                    timeout=None,
                    draw=False
                ):
        """
        bla bla bla
        """

        if not feed_id:
            self.feed_id = uuid.uuid4()
        else:
            self.feed_id = feed_id
        self.buffer_size = buffer_size
        self.cap = cap
        self.params = params
        self.n_ind = n_ind
        self.keep_recordings = keep_recordings
        self.keep_video = keep_video
        self.write_recordings = write_recordings
        self.write_video = write_video
        self.recfile = recfile
        self.datfile = datfile
        self.addr = addr
        self.port_num = port_num
        if timeout is None:
            self.timeout = np.inf
        else:
            self.timeout = timeout
        self.draw = draw

        wait_for_server((addr, port_num))
        self.resmanager = mp.Manager()
        self.manager = SyncManager(address=(addr, port_num), authkey=b'secret')
        self.manager.connect()

        self.semaphore = self.manager.get_semaphore()
        self.port_num = port_num
        self.serverproc = None

        if not "fps" in params:
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        else:
            self.fps = params["fps"]


        self.datashm, self.clockshm = self.setup_shared_mems()
        self.databuffer, self.clockbuffer = self.setup_shared_arrays()

        self.framesbuffer = [np.nan for i in range(int(self.fps * self.buffer_size))]
        self.framesbuffer = self.resmanager.list(self.framesbuffer)
        self.vid_source = "cam"
        if not realtime:
            self.vid_source = "file"


        self.create_feed_file()
        self.casettes = {}

        self.meas_last = [[0, 0] for j in range(self.n_ind)]
        self.meas_now = [[0, 0] for j in range(self.n_ind)]
        self.meas_last = self.resmanager.list(self.meas_last)
        self.meas_now = self.resmanager.list(self.meas_now)
        
    def get_feed_filename(self):
        return joinpath(config.FEEDS_DIR, f"tlfeed-{self.feed_id}")


    def tune_params(self, source="gui"):
        if source == "gui":
            if self.vid_source=="file":
                frame_index = cv2.get(CAP_PROP_POS_FRAMES)
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 1)
            self.params = paramfixing.gui_set_params(cap=self.cap,
                                                vidtype=self.vid_source)
            if self.vid_source=="file":
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)

        elif os.path.exists(source):
            with open(source, "e") as params_json:
                self.params = json.load(params_json)

        else:
            raise ValueError("tune_params argument must be 'gui' or a json filepath.")


    def create_feed_file(self):
        feeddata = {
            "feed_id":      self.feed_id,
            "fps":          self.fps,
            "buffer_size":  self.buffer_size,
            "n_ind":        self.n_ind,
            "datashm":      self.datashm.name,
            "clockshm":     self.clockshm.name,
            "port_num":      self.port_num,
            "vid_source":   self.vid_source,
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

    def __str__(self):
        return f"{self.__class__.__name__} object feed_id:{self.feed_id}"

    def __repr__(self):
        return f"{self.__class__.__name__} object feed_id:{self.feed_id}"

    def __call__(self, f):
        assert callable(f), f"decorate only functions."
        self.casettes[f.__name__] = f
        return f

    def _eachframe(self, databuffer, clockbuffer):#tracking happens here

        try:
            frame, frame_index = trackutils.get_frame(self.cap)
        except EOFError:
            if self.vid_source == "file":
                # file completed
                self.running.value = False
            else:
                pass

        print(self.meas_last, self.meas_now)
        final, contours,\
            self.meas_last, self.meas_now = trackutils.get_contours(
                                            frame=frame,
                                            meas_last=self.meas_last,
                                            meas_now=self.meas_now,
                                            scaling=1.0,#FIXME
                                            draw_contours=self.draw,
                                            **self.params#FIXME:issue in `invert` from paramfixing
                                        )
        print(self.meas_last, self.meas_now)
# FIXME: Hungarian algorithm causes everything to crash whenever no objects detected
        final, self.meas_now = trackutils.cleanup_centroids(
                                    final,
                                    contours,
                                    n_inds=self.n_ind,
                                    meas_last=self.meas_last,
                                    meas_now=self.meas_now,
                                    mot=True,#FIXME
                                    frame_index=frame_index,
                                    draw_circles=self.draw,
                                    use_kmeans=True#FIXME
                                )


        self.semaphore.acquire()
        databuffer[:,:,:-1] = databuffer[:,:,1:]
        clockbuffer[:-1] = clockbuffer[1:]

        clockbuffer[-1] = time.time() - self.t_init
        databuffer[:,:,-1] = self.meas_now[:self.n_ind]#???
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
    cap = cv2.VideoCapture("/home/pranav/Personal/Projects/temp/tracktorlive/Data/vids/fish_video.mp4")
#    cap = cv2.VideoCapture(0)
    semmanager = mp.Process(target=run_semaphore_server)
    semmanager.start()
    server = TracktorServer(
                    cap=cap,
                    params={},
                    n_ind=1,
                    buffer_size=10,#seconds
                    realtime=False,
                    feed_id="trial",
                    keep_recordings=False,
                    keep_video=False,
                    write_recordings=False,
                    write_video=False,
                    recfile=None,
                    datfile=None,
                    addr='127.0.0.1',
                    timeout=None
                )
    server.tune_params()
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
