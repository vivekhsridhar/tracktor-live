# Pranav Minasandra, Vivek H Sridhar, and Isaac Planas-Sitja
# 14 Apr 2025
# pminasandra.github.io

"""
provides class TracktorServer, for underlying tracking and dataserving needs
"""

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
import platformdirs as pfd

import memorymanagement as mmg

APP_NAME = "tracktorlive"
APP_AUTHOR = "DIPV"# Dom, Isaac, Pranav, Vivek
FEEDS_DIR = joinpath(
                pfd.user_data_dir(appname=APP_NAME, appauthor=APP_AUTHOR),
                "LiveFeeds"
                )
os.makedirs(FEEDS_DIR, exist_ok=True)

def _runforever(server):
    t_init = time.time()
    databuffer, clockbuffer = server.setup_shared_arrays()
    while server.running.value:
        server._eachframe(databuffer, clockbuffer)

class SyncManager(BaseManager): pass

def _make_sem():
    return mp.Semaphore(1)

SyncManager.register('get_semaphore', callable=_make_sem)
port_num = random.choice(range(12000, 20000))
def run_semaphore_server():
    manager = SyncManager(address=('127.0.0.1', port_num), authkey=b'secret')
    s = manager.get_server()
    s.serve_forever()

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
                    port_num=port_num
                ):
        """
        bla bla bla
        """

        if not feed_id:
            self.feed_id = uuid.uuid4()
        else:
            self.feed_id = feed_id
        self.buffer_size = buffer_size
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

        wait_for_server((addr, port_num))
        self.manager = SyncManager(address=(addr, port_num), authkey=b'secret')
        self.manager.connect()

        self.semaphore = self.manager.get_semaphore()
        self.port_num = port_num
        self.serverproc = None

        if not "fps" in params:
            self.fps = cap.get(cv2.CAP_PROP_FPS)
        else:
            self.fps = params["fps"]


        self.datashm, self.clockshm = self.setup_shared_mems()
        self.databuffer, self.clockbuffer = self.setup_shared_arrays()

        self.framesbuffer = [np.nan for i in range(int(self.fps * self.buffer_size))]
        self.vid_source = "cam"
        if not realtime:
            self.vid_source = "file"


        self.t_init = time.time()
        self.create_feed_file()
        
# first create a feedobj file
# then set up everything needed for tracking

    def get_feed_filename(self):
        return joinpath(FEEDS_DIR, f"tlfeed-{self.feed_id}")


    def create_feed_file(self):
        feeddata = {
            "feed_id":      self.feed_id,
            "fps":          self.fps,
            "buffer_size":  self.buffer_size,
            "n_ind":        self.n_ind,
            "datashm":      self.datashm.name,
            "clockshm":     self.clockshm,
            "port_nr":      self.port_num,
            "vid_source":   self.vid_source,
            "t_init":       self.t_init,
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
#    def __repr__
#    def __call__#??
    def _eachframe(self, databuffer, clockbuffer):#tracking happens here
        time.sleep(0.02)
        self.semaphore.acquire()
        databuffer[:,:,:-1] = databuffer[:,:,1:]
        clockbuffer[:-1] = clockbuffer[1:]

        clockbuffer[-1] = time.time()
        databuffer[:,:,-1] = np.random.random((self.n_ind, 2))
        self.semaphore.release()
#    def dumpvideo(self, outfile=None)
#    def dumpdata(self, outfile=None)
    def run(self):
        self.running = mp.Value('b', True)
        self.serverproc = mp.Process(target=_runforever, args=(self,))
        self.serverproc.start()

    def stop(self):
        self.running.value = False
        #self.serverproc.terminate()
        self.serverproc.join()
        self.serverproc.close()

    def __del__(self):
        if self.running.value:
            self.stop()
        self.datashm.close()
        self.clockshm.close()
        self.datashm.unlink()
        self.clockshm.unlink()



if __name__ == "__main__":
    cap = cv2.VideoCapture(0)
    semmanager = mp.Process(target=run_semaphore_server)
    semmanager.start()
    server = TracktorServer(
                    cap=cap,
                    params={"fps": 30},
                    n_ind=1,
                    buffer_size=10,#seconds
                    realtime=True,
                    feed_id=None,
                    keep_recordings=False,
                    keep_video=False,
                    write_recordings=False,
                    write_video=False,
                    recfile=None,
                    datfile=None,
                    addr='127.0.0.1'
                )
    server.run()

    tnow = time.time()
    while time.time() - tnow < 10.0:
        print(server.get_data()[:,:,-1], end="\033[K\r")
        time.sleep(0.01)

    server.stop()
    del server
    semmanager.terminate()
    semmanager.join()
    semmanager.close()
