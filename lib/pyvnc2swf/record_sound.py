#!/usr/bin/env python

# record_sound.py - Sound recording routine with PyMedia.
# Contributed by David Fraser

import sys, time
import pymedia.audio.sound as sound
import pymedia.audio.acodec as acodec
import pymedia.muxer as muxer
import threading

class voiceRecorder:
  def __init__(self,  name ):
    self.name = name
    self.finished = False

  def record(self):
    self.snd.start()
    while not self.finished:
      s= self.snd.getData()
      if s and len( s ):
        for fr in self.ac.encode( s ):
          # We definitely should use mux first, but for

          # simplicity reasons this way it'll work also
          block = self.mux.write( self.stream_index, fr )
          if block is not None:
            self.f.write( block )
      else:
        time.sleep( .003 )
        # time.sleep( 0 )
    self.snd.stop()

  def run(self):
    print "recording to", self.name
    self.f= open( self.name, 'wb' )
    # Minimum set of parameters we need to create Encoder

    cparams= { 'id': acodec.getCodecID( 'mp3' ),
               'bitrate': 128000,
               'sample_rate': 44100,
               'channels': 1 }
    self.ac= acodec.Encoder( cparams )
    self.snd= sound.Input( 44100, 1, sound.AFMT_S16_LE )
    self.mux = muxer.Muxer("mp3")
    self.stream_index = self.mux.addStream( muxer.CODEC_TYPE_AUDIO, self.ac.getParams() )
    block = self.mux.start()
    if block:
      self.f.write(block)
    # Loop until Ctrl-C pressed or finished set from outside

    self.finished = False
    thread = threading.Thread(target=self.record)
    thread.start()
    try:
      while not self.finished:
        time.sleep( .003 )
    except KeyboardInterrupt:
      self.finished = True
    print "finishing recording to", self.name
    # Stop listening the incoming sound from the microphone or line in
    thread.join()
    footer = self.mux.end()
    if footer is not None:
      self.f.write(footer)
    self.f.close()
    print "finished recording to", self.name
    print "snipping leading zeroes..."
    f = open( self.name, "rb" )
    buffer = f.read()
    f.close()
    buffer = buffer.lstrip(chr(0))
    f = open( self.name, "wb" )
    f.write( buffer )
    f.close()
    print "snipped leading zeroes"

# ----------------------------------------------------------------------------------

# Record stereo sound from the line in or microphone and save it as mp3 file

# Specify length and output file name

# http://pymedia.org/

if __name__ == "__main__":
  import time
  if len( sys.argv )!= 2:
    print 'Usage: %s <file_name>' % sys.argv[ 0 ]
  else:
    voiceRecorder( sys.argv[ 1 ]  ).run()
