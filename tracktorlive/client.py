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

import tracktorlive
from . import sync

class SyncManager(BaseManager): pass
SyncManager.register('get_semaphore')

def _runforever(obj):
    while obj.running.value:
        try:
            time.sleep(obj.run_interval) #to not overload everything
            obj._eachiter()
        except KeyboardInterrupt:
            obj.running.value=False
            break
        except ConnectionResetError:
            print(f"Server: {obj.feed_id} disconnected.")
            obj.running.value = False
            break

class TracktorClient:

    def __init__(self, feed_id, run_interval=None):
        """
        Initialises a TracktorClient that connects to an existing tracking server.

        Args:
            feed_id (str): Unique ID of the server feed to connect to.
            run_interval (float, optional): Time (in seconds) between successive calls 
                to registered functions. Defaults to 0.005s.

        Raises:
            FileNotFoundError: If the specified feed metadata file does not exist.
            ConnectionRefusedError: If the server cannot be contacted.
        """

        self.feed_id = feed_id
        self.feed_info = self.load_feed_info()
        self.port_num = self.feed_info["port_num"]

        self.client_id = str(uuid.uuid4())
        self.clientfile = self.get_client_filename()
        self.make_client_file()

        sync.wait_for_server((sync.ADDR, self.port_num))
        self.manager = SyncManager(address=('127.0.0.1', self.port_num),
                                        authkey=b'secret')
        self.manager.connect()
        self.semaphore = self.manager.get_semaphore(self.feed_id)

        self.datashm = mpshm.SharedMemory(name=self.feed_info["datashm"])
        self.clockshm = mpshm.SharedMemory(name=self.feed_info["clockshm"])
        mp.resource_tracker.unregister(self.datashm._name, 'shared_memory')
        mp.resource_tracker.unregister(self.clockshm._name, 'shared_memory')
        self.params = self.feed_info["params"]

        self.fps = int(self.feed_info["fps"])
        if run_interval is None:
            self.run_interval = 0.005
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
        return joinpath(tracktorlive.FEEDS_DIR, f"tlfeed-{self.feed_id}")

    def get_client_filename(self):
        return joinpath(tracktorlive.CLIENTS_DIR, f"tlclient-{self.feed_id}-{self.client_id}")

    def make_client_file(self):
        with open(self.clientfile, "a") as f:
            pass

    def load_feed_info(self):
        with open(self.get_feed_filename(), "rb") as f:
            return pickle.load(f)

    def get_data_and_clock(self):
        self.semaphore.acquire()
        data = self.dataq.copy()
        clock = self.clockq.copy()
        self.semaphore.release()
        return data, clock

    def _eachiter(self):
        try:
            data, clock = self.get_data_and_clock()
            if clock[-1] > -1.0-1e-8 and clock[-1] < -1.0 + 1e-8:#FIXME
                self.running.value = False
            else:
                for funcname in self.casettes:
                    self.casettes[funcname](data, clock)
        except EOFError:#server process died
            print("Server died unexpectedly.")
            self.running.value = False

    def run(self):
        """
        Runs all registered functions at specified run interval.
        """
        self.running = mp.Value('b', True)
        self.clientproc = mp.Process(target=_runforever, args=(self,))
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
        if os.path.exists(self.clientfile):
            os.remove(self.clientfile)
        self.datashm.close()
        self.clockshm.close()

def list_feeds():
    """
    Returns a list of all available feed metadata files.

    Returns:
        list[str]: List of paths to active feed files.
    """

    return glob.glob(joinpath(tracktorlive.FEEDS_DIR, "tlfeed-*"))

def spawn_trclient(feed_id, run_interval=0.005):
    """
    Creates and returns a new TracktorClient instance.

    Args:
        feed_id (str): Feed ID of the server to connect to.
        run_interval (float): Interval between iterations in seconds.

    Returns:
        TracktorClient: The initialized client.
    """

    return TracktorClient(feed_id, run_interval)

def close_trclient(client):
    """
    Stops the client and cleans up any associated resources.

    Args:
        client (TracktorClient): The client instance to stop.

    Returns:
        None
    """

    client.stop()

def run_trclient(client):
    """
    Starts the client process for data polling and function execution.

    Args:
        client (TracktorClient): The client instance to run.

    Returns:
        None
    """
    client.run()

def wait_and_close_trclient(client):
    """
    Waits for the client to finish or be interrupted, then closes it.

    Args:
        client (TracktorClient): The client instance to close.

    Returns:
        None

    Raises:
        KeyboardInterrupt: If interrupted during waiting loop.
    """
    try:
        while client.running.value:
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("Terminating client.")
    finally:
        client.stop()


if __name__ == "__main__":

    client = spawn_trclient("trial")

    @client
    def printstuff(data, clock):
        print(clock[-1], data[:,:,-1])

    run_trclient(client)
    del client
