"""
Real-time low-cost animal tracking system.
"""

import os
from os.path import join as joinpath
import platformdirs as pfd

from .server import TracktorServer, spawn_trserver, run_trserver, close_trserver, wait_and_close_trserver, run_trsession
from .client import TracktorClient, spawn_trclient, run_trclient, close_trclient, wait_and_close_trclient, list_feeds
from .paramfixing import gui_set_params as get_params_from_gui

__version__ = "0.1.0"
__author__ = "All the authors here" #FIXME
__license__ = "MIT"
__url__ = "https://github.com/vivekhsridhar/tracktor-live"

__all__ = ['TracktorServer', 'TracktorClient',
            'spawn_trserver', 'run_trserver', 'close_trserver',
            'spawn_trclient', 'run_trclient', 'close_trclient',
            'list_feeds', 'get_params_from_gui'
            ]

APP_NAME = "tracktorlive"
APP_AUTHOR = "Dominique Roche, Isaac Planas-Sitjà, Pranav Minasandra, Vivek H Sridhar"# Dom, Isaac, Pranav, Vivek
FEEDS_DIR = joinpath(
                pfd.user_data_dir(appname=APP_NAME, appauthor=APP_AUTHOR),
                "LiveFeeds"
                )
CLIENTS_DIR = joinpath(
                pfd.user_data_dir(appname=APP_NAME, appauthor=APP_AUTHOR),
                "LiveClients"
                )
os.makedirs(FEEDS_DIR, exist_ok=True)
os.makedirs(CLIENTS_DIR, exist_ok=True)
#Miscellaneous
SUPPRESS_INFORMATIVE_PRINT = False
