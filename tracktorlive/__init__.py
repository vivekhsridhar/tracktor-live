"""
Real-time low-cost animal tracking system.
"""

from .server import TracktorServer, spawn_trserver, run_trserver, close_trserver
from .client import TracktorClient, spawn_trclient, run_trclient, close_trclient

__version__ = "0.1.0"
__author__ = "All the authors here" #FIXME
__license__ = "MIT"

__all__ = ['TracktorServer', 'TracktorClient',
            'spawn_trserver', 'run_trserver', 'close_trserver',
            'spawn_trclient', 'run_trclient', 'close_trclient'
            ]

