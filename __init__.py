import os
import tempfile
from sys import stdout 
from time import sleep

from processing import Process

import lib.messageboard as mb
from lib.pyvnc2swf import vnc2swf

# Get directory for storing files:
_storage_dir = os.environ.get('CASTRO_DATA_DIR',
                             tempfile.gettempdir()) 
#
# Public functions
#
def init():
    global recorder
    recorder = Process(target= vnc2swf.main, args=[[
                        'lib/pyvnc2swf/vnc2swf.py', 
                        '-n', 
                        '-o', os.path.join(_storage_dir, 'castro-video.swf'),
                        'localhost:0']])
def start():
    recorder.start()

def stop():
    mb.recording_should_continue.write(False)

def restart():
    stop()
    init()
    start()

#
# Private functions
#

# Show some output on screen during a test
def _countdown_timer():
    stdout.write("\nRecording a 10 second video...\n\n")
    for i in range(10,0,-1):
        stdout.write("%s " % i)
        stdout.flush()
        sleep(1)
    stdout.write("\n")

def _test():
    init()
    start()
    _countdown_timer()
    stop()

if __name__ == '__main__':
    _test()
