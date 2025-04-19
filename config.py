
# Pranav Minasandra
# pminasandra.github.io
# April 13, 2025

import os
import os.path
from os.path import join as joinpath

import platformdirs as pfd


#Directories
PROJECTROOT = open(".cw", "r").read().rstrip()
DATA = os.path.join(PROJECTROOT, "Data")
FIGURES = os.path.join(PROJECTROOT, "Figures")

formats=['png', 'pdf', 'svg']

APP_NAME = "tracktorlive"
APP_AUTHOR = "DIPV"# Dom, Isaac, Pranav, Vivek
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
