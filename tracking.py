# Pranav Minasandra, Vivek H Sridhar, and Isaac Planas-Sitja
# 14 Apr 2025
# pminasandra.github.io

"""
provides class TracktorServer, for underlying tracking and dataserving needs
"""

class TracktorServer:
    def __init__(self,
                    capture,
                    trackingparams,
                    buffer_size=10,#seconds
                    realtime=True,
                    feed_id=None,
                    keep_recordings=False,
                    keep_video=False,
                    write_recordings=False,
                    write_video=False,
                    recdir=None,
                    datdir=None,
                    addr='127.0.0.1',
                    port=50000
                ):
        """
        bla bla bla
        """
        pass #TODO
# first create a feedobj file
# then set up everything needed for tracking

    def __repr__
    def __call__#??
    def _eachframe(self)#tracking happens here
    def dumpvideo(self, outfile=None)
    def dumpdata(self, outfile=None)
    def run
    def stop
    def __del__



