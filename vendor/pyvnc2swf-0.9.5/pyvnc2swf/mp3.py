#!/usr/bin/env python
##
##  pyvnc2swf - mp3.py
##
##  $Id: mp3.py,v 1.2 2008/07/12 06:06:34 euske Exp $
##
##  Copyright (C) 2005 by Yusuke Shinyama (yusuke at cs . nyu . edu)
##  All Rights Reserved.
##
##  This is free software; you can redistribute it and/or modify
##  it under the terms of the GNU General Public License as published by
##  the Free Software Foundation; either version 2 of the License, or
##  (at your option) any later version.
##
##  This software is distributed in the hope that it will be useful,
##  but WITHOUT ANY WARRANTY; without even the implied warranty of
##  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##  GNU General Public License for more details.
##
##  You should have received a copy of the GNU General Public License
##  along with this software; if not, write to the Free Software
##  Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307,
##  USA.
##

import sys
from struct import pack, unpack
stderr = sys.stderr


##  MP3Storage
##
class MP3Storage:

  def __init__(self, debug=0):
    self.debug = debug
    self.isstereo = None
    self.bit_rate = None
    self.sample_rate = None
    self.initial_skip = 0
    self.frames = []
    #
    self.played_samples = 0
    self.playing_frame = 0
    self.seeksamples = 0
    return

  def __repr__(self):
    return '<MP3Storage: isstereo=%r, bit_rate=%r, sample_rate=%r, initial_skip=%r, frames=%d>' % \
           (self.isstereo, self.bit_rate, self.sample_rate, self.initial_skip, len(self.frames))

  def set_stereo(self, isstereo):
    if self.isstereo == None:
      self.isstereo = isstereo
    elif self.isstereo != isstereo:
      print >>stderr, 'mp3: isstereo does not match!'
    return

  def set_bit_rate(self, bit_rate):
    if self.bit_rate == None:
      self.bit_rate = bit_rate
    elif self.bit_rate != bit_rate:
      print >>stderr, 'mp3: bit_rate does not match! (variable bitrate mp3 cannot be used for SWF)'
    return
  
  def set_sample_rate(self, sample_rate):
    if self.sample_rate == None:
      self.sample_rate = sample_rate
    elif self.sample_rate != sample_rate:
      print >>stderr, 'mp3: sample_rate does not match! (variable bitrate mp3 cannot be used for SWF)'
    return

  def set_initial_skip(self, initial_skip):
    if initial_skip:
      self.initial_skip = initial_skip
    return

  def add_frame(self, nsamples, frame):
    self.frames.append((nsamples, frame))
    return

  def needsamples(self, t):
    return int(self.sample_rate * t) + self.initial_skip

  def get_frames_until(self, t):
    # write mp3 frames
    #
    # Before:
    #
    #   MP3 |----|played_samples
    #   SWF |-------|-----|needsamples(t)
    #             prev   cur.
    #
    # After:
    #                ->|  |<- next seeksamples
    #   MP3 |----------|played_samples
    #   SWF |-------|-----|needsamples(t)
    #             prev   cur.
    needsamples = self.needsamples(t)
    if needsamples < 0:
      return (0, 0, [])
    nsamples = 0
    frames = []
    while self.playing_frame < len(self.frames):
      (samples,data) = self.frames[self.playing_frame]
      if needsamples <= self.played_samples+nsamples+samples: break
      nsamples += samples
      frames.append(data)
      self.playing_frame += 1
    seeksamples = self.seeksamples
    self.played_samples += nsamples
    self.seeksamples = needsamples-self.played_samples # next seeksample
    return (nsamples, seeksamples, frames)

  def seek_frame(self, t):
    needsamples = self.needsamples(t)
    self.played_samples = 0
    for (i,(samples,data)) in enumerate(self.frames):
      if needsamples <= self.played_samples+samples: break
      self.played_samples += samples
      self.playing_frame = i
    self.seeksamples = needsamples-self.played_samples
    return


##  MP3Reader
##
class MP3Reader:

  """
  read MPEG frames.
  """
  
  def __init__(self, storage):
    self.storage = storage
    return

  def read(self, n):
    if self.length != None:
      if self.length <= 0:
        return ''
      self.length -= n
    return self.fp.read(n)

  BIT_RATE = {
    (1,1): (0, 32, 64, 96, 128, 160, 192, 224, 256, 288, 320, 352, 384, 416, 448, 0),
    (1,2): (0, 32, 48, 56,  64,  80,  96, 112, 128, 160, 192, 224, 256, 320, 384, 0),
    (1,3): (0, 32, 40, 48,  56,  64,  80,  96, 112, 128, 160, 192, 224, 256, 320, 0),
    (2,1): (0, 32, 48, 56,  64,  80,  96, 112, 128, 160, 144, 176, 192, 224, 256, 0),
    (2,2): (0,  8, 16, 24,  32,  40,  48,  56,  64,  80,  96, 112, 128, 144, 160, 0),
    (2,3): (0,  8, 16, 24,  32,  40,  48,  56,  64,  80,  96, 112, 128, 144, 160, 0),
    }
  SAMPLE_RATE = {
    3: (44100, 48000, 32000), # V1
    2: (22050, 24000, 16000), # V2
    0: (11025, 12000,  8000), # V2.5
    }
  def read_mp3file(self, fp, length=None, totalsamples0=None, seeksamples=None, verbose=False):
    """parameter seeksamples is ignored."""
    self.fp = fp
    self.length = length
    totalsamples = 0
    while 1:
      x = self.read(4)
      if len(x) < 4: break
      if x.startswith('TAG'):
        # TAG - ignored
        data = x[3]+self.read(128-4)
        if verbose:
          print >>stderr, 'TAG', repr(data)
        continue
      elif x.startswith('ID3'):
        # ID3 - ignored
        id3version = x[3]+fp.read(1)
        flags = ord(fp.read(1))
        s = [ ord(c) & 0x7f for c in fp.read(4) ]
        size = (s[0]<<21) | (s[1]<<14) | (s[2]<<7) | s[3]
        data = fp.read(size)
        if verbose:
          print >>stderr, 'ID3', repr(data)
        continue
      h = unpack('>L', x)[0]
      #if (h & 0xfffb0003L) != 0xfffb0000L: continue
      # All sync bits (b31-21) are set?
      if (h & 0xffe00000L) != 0xffe00000L: continue
      # MPEG Audio Version ID (0, 2 or 3)
      version = (h & 0x00180000L) >> 19
      if version == 1: continue
      # Layer (3: mp3)
      layer = 4 - ((h & 0x00060000L) >> 17)
      if layer == 4: continue
      # Protection
      protected = not (h & 0x00010000L)
      # Bitrate
      b = (h & 0xf000) >> 12
      if b == 0 or b == 15: continue
      # Frequency
      s = (h & 0x0c00) >> 10
      if s == 3: continue
      if version == 3:                      # V1
        bit_rate = self.BIT_RATE[(1,layer)][b]
      else:                                 # V2 or V2.5
        bit_rate = self.BIT_RATE[(2,layer)][b]
      self.storage.set_bit_rate(bit_rate)
      sample_rate = self.SAMPLE_RATE[version][s]
      self.storage.set_sample_rate(sample_rate)
      #print (version, layer, bit_rate, sample_rate)
      nsamples = 1152
      if sample_rate <= 24000:
        nsamples = 576
      pad = (h & 0x0200) >> 9
      channel = (h & 0xc0) >> 6
      self.storage.set_stereo(1-(channel/2))
      joint = (h & 0x30) >> 4
      copyright = bool(h & 8)
      original = bool(h & 4)
      emphasis = h & 3
      if version == 3:
        framesize = 144000 * bit_rate / sample_rate + pad
      else:
        framesize = 72000 * bit_rate / sample_rate + pad
      if protected:
        # skip 16bit CRC
        self.read(2)
      if verbose:
        print >>stderr, 'Frame: bit_rate=%dk, sample_rate=%d, framesize=%d' % \
              (bit_rate, sample_rate, framesize)
      data = x+self.read(framesize-4)
      self.storage.add_frame(nsamples, data)
      totalsamples += nsamples
    if totalsamples0:
      assert totalsamples == totalsamples0
    return


if __name__ == "__main__":
  s = MP3Storage(True)
  MP3Reader(s).read_mp3file(file(sys.argv[1]), verbose=1)
