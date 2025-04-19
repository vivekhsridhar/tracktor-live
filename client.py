# Pranav Minasandra
# pminasandra.github.io
# 14 Apr 2025

"""
Implements class TracktorClient, that provides responses based on the previous
k-second buffer of tracked data.
"""

import glob
import multiprocessing as mp
import multiprocessing.shared_memory as mpshm
from multiprocessing.managers import BaseManager
import os
import os.path
from os.path import join as joinpath
import pickle
import time
import uuid

import numpy as np

import config

def runforever(obj):
    while obj.running.value:
        try:
            time.sleep(0.5*obj.run_interval)
            obj._eachiter()
        except KeyboardInterrupt:
            obj.running.value=False
            break

class SyncManager(BaseManager): pass

class TracktorClient:

    def __init__(self, feed_id, addr='127.0.0.1', run_interval=None):
        """
        initialises a TracktorClient object.
        Args:
            shmname (shared_memory address, see docs): address to last k seconds of data
            configdict: (mp.Manager.dict): configuration dictionary of server
            addr (str) and port_num (int): address specs of the BaseManager for semaphore locks
            run_interval (float): how often attached functions must run. if absent, defaults to 2*FPS
        """

        SyncManager.register('get_semaphore')
        self.feed_id = feed_id
        self.feed_info = self.load_feed_info()
        self.port_num = self.feed_info["port_num"]

        self.client_id = str(uuid.uuid4())
        self.clientfile = self.get_client_filename()
        print(self.clientfile)
        self.make_client_file()
        print(self.clientfile)

        self.manager = SyncManager(address=('127.0.0.1', self.port_num),
                                        authkey=b'secret')
        self.manager.connect()
        self.semaphore = self.manager.get_semaphore()#q: does this not get a different semaphore?

        self.datashm = mpshm.SharedMemory(name=self.feed_info["datashm"])
        self.clockshm = mpshm.SharedMemory(name=self.feed_info["clockshm"])
        mp.resource_tracker.unregister(self.datashm._name, 'shared_memory')
        mp.resource_tracker.unregister(self.clockshm._name, 'shared_memory')
        self.params = self.feed_info["params"]

        self.fps = int(self.feed_info["fps"])
        self.interframe = 1/self.fps
        if run_interval is None:
            self.run_interval = 0.5*self.interframe
        else:
            self.run_interval = run_interval

        self.buffer_size = self.feed_info["buffer_size"]
        self.n_ind = int(self.feed_info["n_ind"])

        self.dataq = np.ndarray(
                    (
                        self.n_ind, #number of individuals as row
                        2, # x, y
                        int(self.fps * self.buffer_size) # number of tracked frames' data in the buffer
                    ),
                    dtype=np.float64,
                    buffer = self.datashm.buf
                )
        self.clockq = np.ndarray(
                    (
                        int(self.fps * self.buffer_size),
                    ),
                    dtype=np.float64,
                    buffer = self.clockshm.buf
                )

        self.casettes = {}
        self.clientproc = None

    def __call__(self, f):
        assert callable(f), "decorate only functions."
        self.casettes[f.__name__] = f
        return f

    def get_feed_filename(self):
        return joinpath(config.FEEDS_DIR, f"tlfeed-{self.feed_id}")

    def get_client_filename(self):
        return joinpath(config.CLIENTS_DIR, f"tlclient-{self.feed_id}-{self.client_id}")

    def make_client_file(self):
        with open(self.clientfile, "a") as f:
            pass

    def load_feed_info(self):
        with open(self.get_feed_filename(), "rb") as f:
            return pickle.load(f)

    def get_data(self):
        self.semaphore.acquire()
        data = self.dataq.copy()
        self.semaphore.release()
        return data

    def get_clock(self):
        self.semaphore.acquire()
        clock = self.clockq.copy()
        self.semaphore.release()
        return clock

    def _eachiter(self):
        try:
            data = self.get_data()
            clock = self.get_clock()
            if clock[-1] > -1.0-1e-8 and clock[-1] < -1.0 + 1e-8:#FIXME
                self.running.value = False
            else:
                for funcname in self.casettes:
                    self.casettes[funcname](data)
        except EOFError:#server process died
            print("Server died unexpectedly.")
            self.running.value = False

    def run(self):
        """
        Runs all registered functions at specified run interval.
        (default: 2*FPS)
        """
        self.running = mp.Value('b', True)
        self.clientproc = mp.Process(target=runforever, args=(self,))
        self.clientproc.start()

    def stop(self):
        """
        Stops running attached functions
        """
        self.running.value = False
        os.remove(self.clientfile)
        #self.clientproc.terminate()
        self.clientproc.join()
        self.clientproc.close()
        
    def __del__(self):
        if self.running.value:
            self.stop()
        self.datashm.close()
        self.clockshm.close()
        if os.path.exists(self.clientfile):
            os.remove(self.clientfile)

def list_feeds():
    return glob.glob(joinpath(config.FEEDS_DIR, "tlfeed-*"))

if __name__ == "__main__":

    client = TracktorClient(feed_id="trial", addr='127.0.0.1', run_interval=0.05)

    @client
    def printstuff(data):
        print(data[:,:,-1], end="\033[K\r")

    client.run()

    time.sleep(10)
    client.stop()
    del client
