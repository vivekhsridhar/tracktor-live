# Pranav Minasandra
# 17 Apr 2025
# pminasandra.github.io

import multiprocessing.shared_memory as mpshm

"""
Utilities for shared memory handling and associated stuff
"""

def create_shared_data(size):
    shm = mpshm.SharedMemory(create=True, size=size)
    return shm
