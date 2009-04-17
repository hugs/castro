import os
import sys
import tempfile
import time

from processing import Process, Queue

import messageboard as mb
from lib.pyvnc2swf import vnc2swf

# Get directory for storing files:
storage_dir = os.environ.get('CASTRO_DATA_DIR',
                             tempfile.gettempdir()) 
vnc = Process(target= vnc2swf.main, args=[[
                    'lib/pyvnc2swf/vnc2swf.py', 
                    '-n', 
                    '-o', os.path.join(storage_dir, 'video.swf'),
                    'localhost:0']])

def start():
    vnc.start()

def make_some_test_output():
    for i in range(10):
        sys.stdout.write("%s " % i)
        sys.stdout.flush()
        time.sleep(1)

def stop():
    mb.loop.write(False)

def main():
    start()
    make_some_test_output()
    stop()


if __name__ == '__main__':
    main()
