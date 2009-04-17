import os
import sys
import tempfile
import time

from processing import Process

import lib.messageboard as mb
from lib.pyvnc2swf import vnc2swf

# Get directory for storing files:
storage_dir = os.environ.get('CASTRO_DATA_DIR',
                             tempfile.gettempdir()) 
#
# Public functions
#
def init():
    global vnc
    vnc = Process(target= vnc2swf.main, args=[[
                        'lib/pyvnc2swf/vnc2swf.py', 
                        '-n', 
                        '-o', os.path.join(storage_dir, 'video.swf'),
                        'localhost:0']])
def start():
    vnc.start()

def stop():
    mb.recording_should_continue.write(False)

def restart():
    stop()
    init()
    start()

# Create some dummy output during a test
def _make_some_test_output():
    sys.stdout.write("\nRecording a 10 second video...\n\n")
    for i in range(11):
        sys.stdout.write("%s " % i)
        sys.stdout.flush()
        time.sleep(1)
    sys.stdout.write("\n")

def test():
    init()
    start()
    _make_some_test_output()
    stop()

if __name__ == '__main__':
    test()
