# Pranav Minasandra
# 25 Apr 2025
# pminasandra.github.io

"""
Synchronisation and semaphore management
"""

import multiprocessing as mp
from multiprocessing.managers import BaseManager
from multiprocessing.synchronize import Semaphore as SemType
import socket
import time

_semaphores = {}

ADDR='127.0.0.1'
class SyncManager(BaseManager): pass

def _make_named_sem(name):
    global _semaphores
    if name not in _semaphores:
        _semaphores[name] = mp.Semaphore(1)
    return _semaphores[name]

SyncManager.register('get_semaphore', callable=_make_named_sem)

def run_semaphore_server(port_num):
    manager = SyncManager(address=(ADDR, port_num), authkey=b'secret')
    s = manager.get_server()
    try:
        s.serve_forever()
    except KeyboardInterrupt:
        s.stop()

def prl_sem_server(port_num):
    serverproc = mp.Process(target=run_semaphore_server, args=(port_num,))
    serverproc.start()
    return serverproc

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
