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
# Create a vnc process handler
vnc = Process(target= vnc2swf.main, args=[[
                    'lib/pyvnc2swf/vnc2swf.py', 
                    '-n', 
                    '-o', os.path.join(storage_dir, 'video.swf'),
                    'localhost:0']])
# Public functions
def start():
    vnc.start()

def stop():
    # Communicate with vnc2swf by telling it to stop looping
    mb.loop.write(False)

# For testing only, really
def _make_some_test_output():
    for i in range(10):
        sys.stdout.write("%s " % i)
        sys.stdout.flush()
        time.sleep(1)

def main():
    start()
    _make_some_test_output()
    stop()

if __name__ == '__main__':
    main()
