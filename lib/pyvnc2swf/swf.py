#!/usr/bin/env python
##
##  pyvnc2swf - swf.py
##
##  $Id: swf.py,v 1.6 2008/11/16 02:39:40 euske Exp $
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

import sys, zlib
from struct import pack, unpack
try:
  from cStringIO import StringIO
except ImportError:
  from StringIO import StringIO
stderr = sys.stderr
lowerbound = max
upperbound = min

CURSOR_DEPTH = 65535


##  DataParser
##
class DataParser:
  
  """
  Low-level byte sequence parser. Inheritable.
  """

  def __init__(self, debug=0):
    self.fp = None
    self.buff = 0
    self.bpos = 8
    self.debug = debug
    return

  def open(self, fname):
    self.fp = file(fname, 'rb')
    return
    
  # fixed bytes read
  
  def read(self, n):
    x = self.fp.read(n)
    if len(x) != n:
      raise EOFError
    return x
  
  def readui8(self):
    return ord(self.read(1))
  def readsi8(self):
    return unpack('<b', self.read(1))[0]
  
  def readui16(self):
    return unpack('<H', self.read(2))[0]
  def readub16(self):
    return unpack('>H', self.read(2))[0]
  def readsi16(self):
    return unpack('<h', self.read(2))[0]
  
  def readub24(self):
    return unpack('>L', '\x00'+self.read(3))[0]

  def readui32(self):
    return unpack('<L', self.read(4))[0]
  def readub32(self):
    return unpack('>L', self.read(4))[0]

  def readrgb(self):
    return ( self.readui8(), self.readui8(), self.readui8() )
  def readrgba(self):
    return ( self.readui8(), self.readui8(), self.readui8(), self.readui8() )

  # fixed bits read

  def setbuff(self, bpos=8, buff=0):
    (self.bpos, self.buff) = (bpos, buff)
    return
  
  def readbits(self, bits, signed=False):
    if bits == 0: return 0
    bits0 = bits
    v = 0
    while 1:
      r = 8-self.bpos # the number of remaining bits we can get from the current buffer.
      if bits <= r:
        # |-----8-bits-----|
        # |-bpos-|-bits-|  |
        # |      |----r----|
        v = (v<<bits) | ((self.buff>>(r-bits)) & ((1<<bits)-1))
        self.bpos += bits
        break
      else:
        # |-----8-bits-----|
        # |-bpos-|---bits----...
        # |      |----r----|
        v = (v<<r) | (self.buff & ((1<<r)-1))
        bits -= r
        self.buff = ord(self.read(1))
        self.bpos = 0
    if signed and (v>>(bits0-1)):
      v -= (1<<bits0)
    return v
  
  # variable length structure

  def readstring(self):
    s = []
    while 1:
      c = self.read(1)
      if c == '\x00': break
      s.append(c)
    return unicode(''.join(s), self.encoding)


##  SWFParser
##
class SWFParser(DataParser):
  
  """
  Low-level SWF parser.
  It invokes do_tagXXX method for every SWF tag.
  """
  
  def __init__(self, debug=0):
    DataParser.__init__(self, debug)
    self.framepos = []
    return

  def open(self, fname, header_only=False):
    DataParser.open(self, fname)
    self.parse_header()
    if header_only: return
    print >>stderr, 'Scanning source swf file: %s...' % fname
    pos = self.fp.tell()
    try:
      while 1:
        x = self.readui16()
        tag = x>>6
        if x & 63 == 63:
          length = self.readui32()
        else:
          length = x & 63
        pos0 = self.fp.tell()
        name = 'scan_tag%d' % tag
        # branch to scan_tag<N>
        if hasattr(self, name):
          getattr(self, name)(tag, length)
        if self.debug:
          data = self.fp.read(length)
          print >>stderr, 'tag=%d, data=%r' % (tag, data)
        else:
          self.fp.seek(pos0+length)
        if tag == 1:
          # next frame
          self.framepos.append(pos)
          pos = self.fp.tell()
    except EOFError:
      pass
    return

  def parse_header(self):
    (F,W,S,V) = self.read(4)
    assert W+S == 'WS'
    self.swf_version = ord(V)
    if 6 <= self.swf_version:
      self.encoding = 'utf-8'
    self.totallen = self.readui32()
    if self.debug:
      print >>stderr, 'Header:', (F,W,S,self.swf_version,self.totallen)
    if F == 'C':
      # compressed
      x = zlib.decompress(self.fp.read())
      self.fp = StringIO(x)
    self.rect = self.readrect()
    self.framerate = self.readui16()/256.0
    self.framecount = self.readui16()
    if self.debug:
      print >>stderr, 'Header:', self.rect, self.framerate, self.framecount
    return

  def parse_frame(self, n):
    self.fp.seek(self.framepos[n])
    if self.debug:
      print >>stderr, 'seek:', n, self.framepos[n]
    try:
      while 1:
        x = self.readui16()
        tag = x>>6
        if x & 63 == 63:
          length = self.readui32()
        else:
          length = x & 63
        pos0 = self.fp.tell()
        name = 'do_tag%d' % tag
        # branch to do_tag<N>
        if hasattr(self, name):
          getattr(self, name)(tag, length)
        else:
          self.do_unknown_tag(tag, length)
        self.fp.seek(pos0+length)
        if tag == 1: break
    except EOFError:
      pass
    return

  def parse_tag1(self):
    x = self.readui16()
    tag = x>>6
    if x & 63 == 63:
      length = self.readui32()
    else:
      length = x & 63
    pos0 = self.fp.tell()
    name = 'do_tag%d' % tag
    # branch to do_tag<N>
    if hasattr(self, name):
      getattr(self, name)(tag, length)
    else:
      self.do_unknown_tag(tag, length)
    self.fp.seek(pos0+length)
    return

  def do_unknown_tag(self, tag, length):
    if self.debug:
      print >>stderr, 'unknown tag: %d, length=%d' % (tag, length)
    return

  def do_tag0(self, tag, length):
    # end
    return

  def readrect(self):
    '''(xmin, xmax, ymin, ymax) NOT width and height!'''
    x = ord(self.read(1))
    bits = x>>3
    self.setbuff(5, x)
    return ( self.readbits(bits,1), self.readbits(bits,1), self.readbits(bits,1), self.readbits(bits,1) )

  def readmatrix(self):
    '''returns (scalex, scaley, rot0, rot1, transx, transy)'''
    self.setbuff()
    (scalex, scaley) = (None, None)
    if self.readbits(1):                # hasscale
      n = self.readbits(5)
      scalex = self.readbits(n,1)/65536.0
      scaley = self.readbits(n,1)/65536.0
    (rot0, rot1) = (None, None)
    if self.readbits(1):                # hasrotate
      n = self.readbits(5)
      rot0 = self.readbits(n,1)/65536.0
      rot1 = self.readbits(n,1)/65536.0
    (transx, transy) = (None, None)
    n = self.readbits(5)
    transx = self.readbits(n,1)
    transy = self.readbits(n,1)
    return (scalex, scaley, rot0, rot1, transx, transy)

  def readgradient(self, version):
    n = self.readui8()
    r = []
    for i in xrange(n):
      ratio = self.readui8()
      if version < 3:
        color = self.readrgb()
      else:
        color = self.readrgba()
      r.append((ratio, color))
    return r

  def read_style(self, version):
    '''
    fillstyles: list of (color, matrix, gradient, bitmapid, bitmapmatrix)
    linestyles: list of (width, color)
    '''
    # fillstylearray
    fillstyles = []
    nfills = self.readui8()
    if 2 <= version and nfills == 0xff:
      nfills = self.readui16()
    for i in xrange(nfills):
      t = self.readui8()
      (color, matrix, gradient, bitmapid, bitmapmatrix) = (None, None, None, None, None)
      if t == 0x00:
        if version == 3:
          color = self.readrgba()
        else:
          color = self.readrgb()
      elif t in (0x10, 0x12):
        matrix = self.readmatrix()
        gradient = self.readgradient(version)
      elif t in (0x40, 0x41, 0x42, 0x43):
        bitmapid = self.readui16()
        bitmapmatrix = self.readmatrix()
      fillstyles.append((color, matrix, gradient, bitmapid, bitmapmatrix))
    # linestylearray
    linestyles = []
    nlines = self.readui8()
    if 2 <= version and nlines == 0xff:
      nlines = self.readui16()
    for i in xrange(nlines):
      width = self.readui16()
      if version == 3:
        color = self.readrgba()
      else:
        color = self.readrgb()
      linestyles.append((width, color))
    return (fillstyles, linestyles)

  def read_shape(self, version, fillstyles=[], linestyles=[]):
    self.setbuff()
    nfillbits = self.readbits(4)
    nlinebits = self.readbits(4)
    r = []
    while 1:
      typeflag = self.readbits(1)
      if typeflag:
        # edge spec.
        straightflag = self.readbits(1)
        if straightflag:
          # StraightEdgeRecord
          n = self.readbits(4)+2
          if self.readbits(1):
            dx = self.readbits(n,1)
            dy = self.readbits(n,1)
            r.append( (1,(dx,dy)) )
          elif self.readbits(1):
            dy = self.readbits(n,1)
            r.append( (1,(0,dy)) )
          else:
            dx = self.readbits(n,1)
            r.append( (1,(dx,0)) )
        else:
          # CurveEdgeRecord
          n = self.readbits(4)+2
          cx = self.readbits(n,1)
          cy = self.readbits(n,1)
          ax = self.readbits(n,1)
          ay = self.readbits(n,1)
          r.append( (2,(cx,cy),(ax,ay)) )
      else:
        # style spec.
        flags = self.readbits(5)
        if flags == 0: break
        if flags & 1:
          n = self.readbits(5)
          x0 = self.readbits(n,1)
          y0 = self.readbits(n,1)
          r.append( (0,(x0,y0)) )
        if flags & 2:
          fillstyle0 = self.readbits(nfillbits)
        if flags & 4:
          fillstyle1 = self.readbits(nfillbits)
        if flags & 8:
          linestyle1 = self.readbits(nlinebits)
        if flags & 16:
          (fillstyles, linestyles) = self.read_style(version)
          nfillbits = self.readbits(4)
          nlinebits = self.readbits(4)
    return r


##  FLVParser
##
class FLVParser(DataParser):
  
  def __init__(self, debug=0):
    DataParser.__init__(self, debug)
    self.tags = []
    return

  def open(self, fname, header_only=False):
    DataParser.open(self, fname)
    self.parse_header()
    if header_only: return
    print >>stderr, 'Scanning source flv file: %s...' % fname
    try:
      offset = self.readub32()          # always 0
      while 1:
        tag = self.readui8()
        length = self.readub24()
        timestamp = self.readub24()     # timestamp in msec.
        reserved = self.readub32()
        offset = self.fp.tell()
        self.tags.append((tag, length, timestamp, offset))
        self.fp.seek(offset + length + 4)  # skip PreviousTagSize
    except EOFError:
      pass
    return

  def parse_header(self):
    (F,L,V,ver) = self.read(4)
    assert F+L+V == 'FLV'
    self.flv_version = ord(ver)
    flags = self.readui8()
    offset = self.readub32()
    if self.debug:
      print >>stderr, 'Header:', (F,L,V,self.flv_version,flags)
    return

  def get_tag(self, i):
    (tag, length, timestamp, offset) = self.tags[i]
    self.fp.seek(offset)
    data = self.read(length)
    return (tag, timestamp, data)

  def seek_tag(self, t):
    i0 = 0
    i1 = len(self.tags)
    while i0 < i1:
      i = (i0+i1)/2
      (tag, length, timestamp, offset) = self.tags[i]
      if timestamp < t:
        i0 = i
      else:
        i1 = i
    return (tag, length, timestamp, offset)
  

##  SWFWriter
##

# return the number of required bits for x.
def needbits1(x, signed=False):
  if x == 0:
    return 0
  if signed:
    n = 1
    if x < 0:
      x = -x-1
  else:
    n = 0
    assert 0 < x
  while 1:
    n += 1
    x >>= 1
    if x == 0: break
  return n

def needbits(args, signed=False):
  return max([ needbits1(x, signed) for x in args ])
# assert needbits1(0,0) == 0
# assert needbits1(0,1) == 0
# assert needbits1(1,0) == 1
# assert needbits1(1,1) == 2
# assert needbits1(2,0) == 2
# assert needbits1(-2,1) == 2
# assert needbits1(-3,1) == 3
# assert needbits1(127,0) == 7
# assert needbits1(127,1) == 8
# assert needbits1(128,0) == 8
# assert needbits1(-128,1) == 8
# assert needbits1(-129,1) == 9
# assert needbits1(-6380,1) == 14

##  DataWriter
##  A common superclass for SWFWriter and FLVWriter
##
class DataWriter:

  def push(self):
    self.fpstack.append(self.fp)
    self.fp = StringIO()
    return

  def pop(self):
    assert self.fpstack, 'empty fpstack'
    self.fp.seek(0)
    data = self.fp.read()
    self.fp = self.fpstack.pop()
    return data

  # fixed bytes write
  
  def write(self, *args):
    for x in args:
      self.fp.write(x)
    return

  def writeui8(self, *args):
    for x in args:
      self.fp.write(chr(x))
    return
  def writesi8(self, *args):
    for x in args:
      self.fp.write(pack('<b', x))
    return
  
  def writeui16(self, *args):
    for x in args:
      self.fp.write(pack('<H', x))
    return 
  def writeub16(self, *args):
    for x in args:
      self.fp.write(pack('>H', x))
    return 
    
  def writesi16(self, *args):
    for x in args:
      self.fp.write(pack('<h', x))
    return
  
  def writeub24(self, *args):
    for x in args:
      self.fp.write(pack('>L', x)[1:4])
    return

  def writeui32(self, *args):
    for x in args:
      self.fp.write(pack('<L', x))
    return
  def writeub32(self, *args):
    for x in args:
      self.fp.write(pack('>L', x))
    return

  def writergb(self, (r,g,b)):
    self.writeui8(r,g,b)
    return
  def writergba(self, (r,g,b,a)):
    self.writeui8(r,g,b,a)
    return

  # fixed bits write
  def writebits(self, bits, x, signed=False):
    if signed and x < 0:
      x += (1<<bits)
    assert 0 <= x and x < (1<<bits)
    while 1:
      r = 8-self.bpos # the number of remaining bits we can write into the current buffer.
      if bits <= r:
        # |-----8-bits-----|
        # |-bpos-|-bits-|  |
        # |      |----r----|
        self.buff |= x << (r-bits)
        self.bpos += bits               # <= 8
        break
      else:
        # |-----8-bits-----|
        # |-bpos-|---bits----...
        # |      |----r----|
        self.fp.write(chr(self.buff | (x >> (bits-r)))) # r < bits
        self.buff = 0
        self.bpos = 0
        bits -= r                      # cut the upper r bits
        x &= (1<<bits)-1
    return
  
  def finishbits(self):
    if self.bpos:
      self.fp.write(chr(self.buff))
      self.buff = 0
      self.bpos = 0
    return
  
  # variable length structure
  
  def writestring(self, s):
    assert '\x00' not in s
    self.write(s)
    self.write('\x00')
    return

  def writerect(self, (xmin,xmax,ymin,ymax)):
    '''NOT width and height!'''
    assert xmin <= xmax and ymin <= ymax
    n = needbits((xmin,xmax,ymin,ymax), 1)
    self.writebits(5, n)
    self.writebits(n, xmin, 1)
    self.writebits(n, xmax, 1)
    self.writebits(n, ymin, 1)
    self.writebits(n, ymax, 1)
    self.finishbits()
    return

  def writematrix(self, (scalex,scaley, rot0,rot1, transx,transy)):
    if scalex != None:
      scalex = int(scalex*65536)
      scaley = int(scaley*65536)
      self.writebits(1, 1)
      n = needbits((scalex,scaley), 1)
      assert n < 32, 'too many bits needed'
      self.writebits(5, n)
      self.writebits(n, scalex, 1)
      self.writebits(n, scaley, 1)
    else:
      self.writebits(1, 0)
    if rot0 != None:
      self.writebits(1, 1)
      rot0 = int(rot0*65536)
      rot1 = int(rot1*65536)
      n = needbits((rot0,rot1), 1)
      assert n < 32, 'too many bits needed'
      self.writebits(5, n)
      self.writebits(n, rot0, 1)
      self.writebits(n, rot1, 1)
    else:
      self.writebits(1, 0)
    n = needbits((transx, transy), 1)
    assert n < 32, 'too many bits needed'
    self.writebits(5, n)
    self.writebits(n, transx, 1)
    self.writebits(n, transy, 1)
    self.finishbits()
    return

  def write_style(self, version, fillstyles, linestyles):
    # fillstyle
    if 254 < len(fillstyles):
      assert 2 <= version
      self.writeui8(0xff)
      self.writeui16(len(fillstyles))
    else:
      self.writeui8(len(fillstyles))
    for (t,color,matrix,gradientmatrix,bitmapid,bitmapmatrix) in fillstyles:
      self.writeui8(t)
      if color != None:
        assert t == 0x00
        if version == 3:
          self.writergba(color)
        else:
          self.writergb(color)
      elif gradientmatrix != None:
        assert t in (0x10, 0x12)
        self.writematrix(gradientmatrix)
        #self.writegradient(gradient, version)
      elif bitmapid != None and bitmapmatrix != None:
        assert t in (0x40, 0x41, 0x42, 0x43)
        self.writeui16(bitmapid)
        self.writematrix(bitmapmatrix)
      else:
        assert 0, 'illegal arg: %d' % t
    # linestyle
    if 254 < len(linestyles):
      assert 2 <= version
      self.writeui8(0xff)
      self.writeui16(len(linestyles))
    else:
      self.writeui8(len(linestyles))
    for (width,color) in linestyles:
      self.writeui16(width)
      if version == 3:
        self.writergba(color)
      else:
        self.writergb(color)
    return

  # simple shape - up to only one fill/linestyle
  def write_shape(self, version, points, fillstyle=None, linestyle=None):
    assert 2 <= len(points)
    flags = 0 # moveto
    fillbits = 0
    if fillstyle != None:
      fillbits = needbits1(fillstyle)
      flags |= 2 # fillstyle1
    linebits = 0
    if linestyle != None:
      linebits = needbits1(linestyle)
      flags |= 4 # linestyle
    self.writebits(4, fillbits)
    self.writebits(4, linebits)
    # set the style and initial position
    (t,(x0,y0)) = points[0]
    assert t == 0
    self.writebits(1, 0) # typeflag:0
    self.writebits(4, flags)
    self.writebits(1, 1) # moveto:1
    n = needbits((x0,y0), 1)
    self.writebits(5, n)
    self.writebits(n, x0, 1)
    self.writebits(n, y0, 1)
    if fillstyle != None:
      self.writebits(fillbits, fillstyle)
    if linestyle != None:
      self.writebits(linebits, linestyle)
    # put points
    for pt in points[1:]:
      t = pt[0]
      self.writebits(1, 1) # edgetype
      if t == 1:
        (t,(dx,dy)) = pt
        self.writebits(1, 1) # StraightEdgeRecord
        if dx == 0:
          n = lowerbound(needbits1(dy, 1), 2)
          self.writebits(4, n-2)
          self.writebits(1, 0) # write only
          self.writebits(1, 1) # dy
          self.writebits(n, dy, 1)
        elif dy == 0:
          n = lowerbound(needbits1(dx, 1), 2)
          self.writebits(4, n-2)
          self.writebits(1, 0) # write only
          self.writebits(1, 0) # dx
          self.writebits(n, dx, 1)
        else:
          n = lowerbound(needbits((dx,dy), 1), 2)
          self.writebits(4, n-2)
          self.writebits(1, 1) # write dx and dy
          self.writebits(n, dx, 1)
          self.writebits(n, dy, 1)
      elif t == 2:
        (t,(cx,cy),(ax,ay)) = pt
        n = lowerbound(needbits((cx,cy,ax,ay), 1), 2)
        self.writebits(4, n-2)
        self.writebits(n, cx, 1)
        self.writebits(n, cy, 1)
        self.writebits(n, ax, 1)
        self.writebits(n, ay, 1)
        (x0,y0) = (ax,ay)
      else:
        assert 0
    self.writebits(1, 0) # styletype
    self.writebits(5, 0) # EOS
    self.finishbits()
    return

  def start_tag(self):
    self.push()
    return
  
  def start_action(self):
    self.start_tag()
    return
  
  def do_action(self, action, length=None):
    assert action < 128 or length != None
    self.writeui8(action)
    if 128 <= action:
      self.writeui16(length)
    return
  
  def end_action(self):
    self.writeui8(0)                    # End
    self.end_tag(12)                    # DoAction
    return


##  SWFWriter
##
class SWFWriter(DataWriter):

  """
  Low-level SWF generator.
  It handles some primitive data types and compression.

  w = SWFWriter('out.swf', 5, (0,0,640,480), True)
  w.start_tag()
  w.writeui32(...)
  w.end_tag(1)
  ...
  w.write_file(10)
  """

  def __init__(self, outfile, swf_version, rect, framerate, compression):
    if outfile == '-':
      raise VelueError('cannot write a SWF file to stdout.')
    self.outfp = file(outfile, 'wb')
    self.swf_version = swf_version
    self.rect = rect
    self.framerate = framerate
    self.compression = compression
    self.fpstack = []
    self.bpos = 0
    self.buff = 0
    self.objid = 0
    if self.compression:
      self.fp = StringIO()
      self.fp.write('CWS%c' % self.swf_version)
    else:
      self.fp = self.outfp
      self.fp.write('FWS%c' % self.swf_version)
    self.lenpos = self.fp.tell()
    self.writeui32(0) # dummy length
    self.writerect(rect)
    self.writeui16(int(framerate * 256))
    self.fcpos = self.fp.tell()
    self.writeui16(0) # dummy framecount
    return

  def newid(self):
    self.objid += 1
    assert self.objid < 65536, 'the number of objects exceeded the limit!'
    return self.objid

 # flush the buffer, the file is closed.
  def write_file(self, framecount):
    assert not self.fpstack, 'nonempty fpstack: %r' % self.fpstack
    self.fp.seek(0, 2) # seek to the last
    length = self.fp.tell()
    self.fp.seek(self.lenpos)
    self.writeui32(length) # adjust the length
    self.fp.seek(self.fcpos)
    self.writeui16(framecount) # adjust the framecount
    if self.compression:
      self.fp.seek(0)
      data = self.fp.read(8)
      self.outfp.write(data)
      data = self.fp.read()
      self.outfp.write(zlib.compress(data))
    self.outfp.close()
    return

  def end_tag(self, tag, forcelong=False):
    data = self.pop()
    if 63 <= len(data) or forcelong:
      self.writeui16(tag << 6 | 63)
      self.writeui32(len(data))
    else:
      self.writeui16(tag << 6 | len(data))
    self.write(data)
    return


##  FLVWriter
##  Contributed by Luis Fernando <lfkpoa-69@yahoo.com.br>
##
class FLVWriter(DataWriter):
  
  def __init__(self, outfile, flv_version, rect, framerate):
    if outfile == '-':
      self.outfp = sys.stdout
    else:
      self.outfp = file(outfile, 'wb')
    self.rect = rect
    self.flv_version = flv_version
    self.framerate = framerate
    self.fpstack = []
    self.bpos = 0
    self.buff = 0
    self.fp = self.outfp
    self.fp.write('FLV%c' % self.flv_version)
    self.writebits(5,0)
    self.writebits(1,0) # has audio
    self.writebits(1,0)
    self.writebits(1,1) # has video
    self.finishbits()
    self.writeub32(9) # dataoffset (header size) = 9
    self.writeub32(0) # previous tag size = 0
    return

  def end_tag(self, tag, timestamp):
    data = self.pop()
    self.writeui8(tag)
    self.writeub24(len(data))
    self.writeub24(int(timestamp))
    self.writeui32(0)   # reserved
    self.write(data)
    self.writeub32(len(data)+11)  #size of this tag
    return

  def write_file(self, framecount):
    self.outfp.close()
    return


# test
if __name__ == "__main__":
  parser = FLVParser(True)
  parser.open(sys.argv[1])
