import os
import tempfile
from datetime import datetime, timedelta
from sys import stdout 
from time import sleep

from multiprocessing import Process
import yaml

import lib.messageboard as mb
from lib.pyvnc2swf import vnc2swf

# Get directory for storing files:
DATA_DIR = os.environ.get('CASTRO_DATA_DIR',
                          tempfile.gettempdir()) 

class Castro:
    def __init__(s, 
                 filename = "castro-video.swf",
                 host     = "localhost",
                 display  = 0,
                 framerate = 12,
                 clipping = None,
                 passwd   = os.path.join(os.path.expanduser("~"), ".vnc", "passwd")):
        s.filename = filename
        s.filepath = os.path.join(DATA_DIR, s.filename)
        s.host = host
        s.display = display
        s.framerate = framerate
        s.clipping = clipping
        s.passwd = passwd
        
        # Post-process data: 
        s.duration = 0        
        s.tempfilepath = os.path.join(DATA_DIR, 'temp-' + s.filename)
        s.cuefilepath = os.path.join(DATA_DIR, s.filename + "-cuepoints.xml")

        # Finally...
        s.init()

    def init(s):
        args=['lib/pyvnc2swf/vnc2swf.py', 
               '-n',
               '-o', s.filepath,
               '%s:%s' % (s.host, s.display) ]

        # If password file is specified, insert it into args
        if s.passwd:
            args.insert(4, '-P')
            args.insert(5, s.passwd)

        # If framerate is specified, insert it into args
        if s.framerate:
            args.insert(4, '-r')
            args.insert(5, s.framerate)

        # If clipping is specified, insert it into args
        if s.clipping:
            args.insert(4, '-C')
            args.insert(5, s.clipping)

        s.recorder = Process(target= vnc2swf.main, args=[args])

    def start(s):
        s.recorder.start()

    def stop(s):
        mb.recording_should_continue.write(False)
        s.recorder.join()

    def restart(s):
        s.stop()
        s.init()
        s.start()

    def process(s):
        s.keyframe()
        s.calc_duration()
        s.cuepoint()
        s.inject_metadata()
        s.cleanup()

    def keyframe(s):
        print "Running ffmpeg: creating keyframes"
        os.system("ffmpeg -y -i %s -g %s -sameq %s" %
          (s.filepath,
           s.framerate,
           s.tempfilepath))

    def calc_duration(s):
        print "Getting Duration:"  
        flv_data_raw = os.popen("flvtool2 -P %s" % s.tempfilepath).read()
        flv_data = yaml.load(flv_data_raw)
        s.duration = int(round(flv_data[flv_data.keys()[0]]['duration']))
        print "Duration: %s" % s.duration

    def cuepoint(s):
        print "\n\nCreating cuepoints:"
        # Create the cuepoints file
        cuefile = open(s.cuefilepath,'w') 

        # Write the header
        cuefile.write ("<?xml version=\"1.0\"?>\n")
        cuefile.write ("<tags>\n")
        cuefile.write ("  <!-- navigation cue points -->\n")

        # Write the body
        for i in range(0,s.duration,1):
            name = (datetime(1900,1,1,0,0,0) + timedelta(seconds=i)).strftime('%H:%M:%S')
            cuefile.write ("  <metatag event=\"onCuePoint\">\n")
            cuefile.write ("    <name>%s</name>\n" % name)
            cuefile.write ("    <timestamp>%s000</timestamp>\n" % i)
            cuefile.write ("    <type>navigation</type>\n")
            cuefile.write ("  </metatag>\n")


        # Write the footer
        cuefile.write ("</tags>\n")
        cuefile.close()

    def inject_metadata(s):
        os.system("flvtool2 -AUt %s %s %s" %
            (s.cuefilepath,
             s.tempfilepath,
             s.filepath))

    def cleanup(s):
        os.remove(s.cuefilepath)
        os.remove(s.tempfilepath)


# To be used with a "with" statement
class video:
    def __init__(s, *args, **kwargs):
        s.recorder = Castro(*args, **kwargs)
    
    def __enter__(s):
        s.recorder.start()
    
    def __exit__(s, type, value, traceback):
        s.recorder.stop()

# Show some output on screen during a test
def countdown_timer():
    stdout.write("\nRecording a 10 second video...\n\n")
    for i in range(10,0,-1):
        stdout.write("%s " % i)
        stdout.flush()
        sleep(1)
    stdout.write("\n")

def test():
    c = Castro()
    c.init()
    c.start()
    countdown_timer()
    c.stop()

if __name__ == '__main__':
    test()
