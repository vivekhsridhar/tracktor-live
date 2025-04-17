# Pranav Minasandra
# pminasandra.github.io
# 14 Apr 2025

"""
Implements class TracktorClient, that provides responses based on the previous
k-second buffer of tracked data.
"""

import multiprocessing as mp
import multiprocessig.shared_memory as mpshm
import time

import numpy as np

def runforever(obj):
    while True:
        time.sleep(0.5*obj.run_interval)
        obj._eachiter()

class SyncManager(BaseManager): pass

class TracktorClient:

    def __init__(self, shmname, configdict, addr='127.0.0.1', port_num=50000, run_interval=None):
        """
        initialises a TracktorClient object.
        Args:
            shmname (shared_memory address, see docs): address to last k seconds of data
            configdict: (mp.Manager.dict): configuration dictionary of server
            addr (str) and port_num (int): address specs of the BaseManager for semaphore locks
            run_interval (float): how often attached functions must run. if absent, defaults to 2*FPS
        """

        SyncManager.register('get_semaphore')

        self.manager = SyncManager(address=('127.0.0.1', port_num), authkey=b'secret')
        self.manager.connect()
        self.sem = self.manager.get_semaphore()

        self.shmname = shmname
        self.config = configdict

        self.fps = int(self.config["fps"])
        self.interframe = 1/self.fps
        if run_interval is None:
            self.run_interval = 0.5*self.interframe
        else:
            self.run_interval = run_interval

        self.bufferdur = self.config["bufferdur"]
        self.n_ind = int(self.config["n_ind"])

        self.shm = mpshm.SharedMemory(name=self.shmname)
        self.dataq = np.ndarray(
                    (
                        self.n_ind, #number of individuals as row
                        2, # x, y
                        int(self.fps * self.bufferdur) # number of tracked frames' data in the buffer
                    ),
                    dtype=np.float64,
                    buffer = self.shm.buf
                )

        self.tgtfuncs = {}
        self.clientproc = None

    def __call__(self, f):
        self.tgtfuncs[f.__name__] = f
        return f

    def _eachiter(self):
        with self.sem
            for funcname in self.tgtfuncs:
                self.tgtfuncs[funcname](self.dataq)

    def run(self):
        """
        Runs all registered functions at specified run interval.
        (default: 2*FPS)
        """
        self.clientproc = mp.Process(target=runforever, args=(self,))
        self.clientproc.start()

    def stop(self):
        """
        Stops running attached functions
        """
        self.clientproc.terminate()
        self.clientproc.join()
        self.clientproc.close()
        
    def __del__(self, f):
        self.stop()
        self.shm.close()
