#!/usr/bin/env python
##
##  pyvnc2swf - output.py
##
##  $Id: output.py,v 1.8 2008/11/16 02:39:40 euske Exp $
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
from swf import SWFWriter, FLVWriter, CURSOR_DEPTH
from image import *
stderr = sys.stderr
lowerbound = max
upperbound = min


##  SWFScreen
##
class SWFScreen:

  """
  SWFScreen is a framebuffer which is temporarily used
  for movie construction.
  """
  
  def __init__(self, x0, y0, w, h, scaling=None):
    (self.x0, self.y0, self.width, self.height) = (x0, y0, w, h)
    self.scaling = scaling
    if scaling:
      (self.out_width, self.out_height) = (int(w*scaling), int(h*scaling))
    else:
      (self.out_width, self.out_height) = (w, h)
    self.buf = create_image(w, h)
    self.out_buf = None
    return
  
  def __repr__(self):
    return '<SWFScreen: %dx%d at (%d, %d), output=%dx%d>' % \
           (self.width, self.height, self.x0, self.y0, self.out_width, self.out_height)

  def adjust_cursor_pos(self, (x,y), (dx,dy)):
    x = x - self.x0 - dx
    y = y - self.y0 - dy
    if self.scaling:
      x *= self.scaling
      y *= self.scaling
    return (int(x), int(y))

  def prepare_image(self, cursor_image=None, cursor_offset=None, cursor_pos=None):
    # do proper scaling
    if self.scaling:
      self.out_buf = scale_image(self.buf, self.scaling)
    elif cursor_image and cursor_pos and cursor_offset:
      self.out_buf = create_image(self.out_width, self.out_height)
      paste_image(self.out_buf, self.buf, (0, 0))
    else:
      self.out_buf = self.buf
    if cursor_image and cursor_pos and cursor_offset:
      cursor_pos = self.adjust_cursor_pos(cursor_pos, cursor_offset)
      paste_image(self.out_buf, cursor_image, cursor_pos)
    return self.out_buf

  def get_image(self, x, y, w, h):
    #assert 0 <= x and 0 <= y, (x,y)
    return crop_image(self.out_buf, (x, y, w, h))

  def dump_image(self, fname):
    save_image(self.out_buf, fname)
    return

  # returns True if the image is actually painted.
  def paint_image(self, x0, y0, w, h, (format, data)):
    x0 -= self.x0
    y0 -= self.y0
    if not (w and h and 0 < x0+w and x0 < self.width and 0 < y0+h and y0 < self.height):
      return False
    if format == IMG_SOLID:
      # fill color
      solid_fill(self.buf, (x0, y0, w, h), data)
      return True
    if format == IMG_RAW:
      # raw buffer (RGB or RGBX)
      if len(data) == (w*h*3):
        img = create_image_from_string_rgb(w, h, data)
      elif len(data) == (w*h*4):
        img = create_image_from_string_rgbx(w, h, data)
      else:
        assert 0
    elif format == IMG_LOSSLESS:
      # image defined by DefineBitsLossless (XRGB)
      data = zlib.decompress(data)
      assert len(data) == (w*h*4)
      img = create_image_from_string_xrgb(w, h, data)
    elif format == IMG_VIDEOPACKET:
      # image defined by SCREENVIDEOPACKET (BGR)
      data = zlib.decompress(data)
      assert len(data) == (w*h*3)
      img = create_image_from_string_rgb_flipped(w, h, bgr2rgb(data))
    else:
      assert 0, 'illegal image format: %d' % format
    # sometime the pasted image doesn't fit in the screen, but just let it out.
    paste_image(self.buf, img, (x0, y0))
    return True


##  SWFBlockScreen
##
class SWFBlockScreen(SWFScreen):

  """SWFBlockScreen is a blockized SWFScreen."""
  
  def __init__(self, x0, y0, w, h, block_w, block_h, scaling=None):
    SWFScreen.__init__(self, x0, y0, w, h, scaling=scaling)
    self.block_w = block_w
    self.block_h = block_h
    if scaling:
      (w,h) = (int(w*scaling), int(h*scaling))
    self.hblocks = (w+self.block_w-1)/self.block_w
    self.vblocks = (h+self.block_h-1)/self.block_h
    return


##  SWFShapeScreen
##
class SWFShapeScreen(SWFBlockScreen):

  """
  SWFShapeScreen is a SWFBlockScreen which consists of
  overlapping objects of images. This is used by SWFShapeStream.
  """
  
  MAPBLOCKSIZE = 4
  
  class SWFShapeRef:
    def __init__(self, depth, count):
      self.depth = depth
      self.count = count
      return
    def __repr__(self):
      return '(%d,%d)' % (self.depth, self.count)

  def __init__(self, x0, y0, w, h, scaling=None):
    SWFBlockScreen.__init__(self, x0, y0, w, h, self.MAPBLOCKSIZE, self.MAPBLOCKSIZE,
                            scaling=scaling)
    self.map = None
    self.current_depth = 1
    self.last_depth = 1
    return
  
  def initmap(self):
    self.map = [ [None]*self.hblocks for i in xrange(self.vblocks) ]
    return

  def next_frame(self):
    self.last_depth = self.current_depth
    return

  # x0,y0,w,h: output rectangle (scaled)
  def place_object(self, added, x0, y0, w, h, replaced):
    x0 -= self.x0
    y0 -= self.y0
    if x0+w <= 0 or self.out_width <= x0 or y0+h <= 0 or self.out_height <= y0:
      return
    x1 = upperbound((x0+w)/self.block_w+1, self.hblocks)
    y1 = upperbound((y0+h)/self.block_h+1, self.vblocks)
    x0 = lowerbound(x0/self.block_w, 0)
    y0 = lowerbound(y0/self.block_h, 0)
    depth0 = self.last_depth
    for y in xrange(y0, y1):
      line = self.map[y]
      for x in xrange(x0, x1):
        obj0 = line[x]
        if not obj0 or obj0.depth < depth0:
          depth0 = -1
          break
      if depth0 == -1: break
    else:
      return

    obj1 = SWFShapeScreen.SWFShapeRef(self.current_depth, (x1-x0)*(y1-y0))
    self.current_depth += 1
    # find completely covered objects (whose ref==0).
    for line in self.map[y0:y1]:
      for x in xrange(x0, x1):
        obj0 = line[x]
        if obj0:
          obj0.count -= 1
          if obj0.count == 0:
            replaced[obj0.depth] = 1
        line[x] = obj1
    
    added.append((obj1.depth, x0*self.block_w, y0*self.block_h, (x1-x0)*self.block_w, (y1-y0)*self.block_h))
    return


##  SWFVideoScreen
##
class SWFVideoScreen(SWFBlockScreen):
  
  """
  SWFVideoScreen is a SWFBlockScreen which consists of a grid of
  blocks. This is used by SWFVideoStream.
  """

  def __init__(self, x0, y0, w, h, block_w, block_h, scaling=None):
    SWFBlockScreen.__init__(self, x0, y0, w, h, block_w, block_h,
                            scaling=scaling)
    return

  def init_blocks(self):
    self.block_changed = [ [True]*self.hblocks for i in xrange(self.vblocks) ]
    self.block_image = [ [None]*self.hblocks for i in xrange(self.vblocks) ]
    return

  # must return a string!
  def get_block_change(self, x, y):
    # okay, this function is going to be called millions of times.
    # so it must perform ultra-fast.
    '''get change of block (x,y)'''
    if not self.block_changed[y][x]:
      return ''
    x0 = x*self.block_w
    y0 = self.out_height-(y+1)*self.block_h
    # if the block is partial, the player also expects a partial image.
    w = upperbound(self.block_w, self.out_width-x0)
    h = self.block_h
    if y0 < 0:
      h += y0
      y0 = 0
    # for some reason y-axis is filpped in VideoPacket.
    # so we flip it in advance so that it can go back correctly...
    data = convert_image_to_string_rgb_flipped(self.get_image(x0, y0, w, h))
    hval = hash(data)
    if self.block_image[y][x] == hval:
      return ''
    self.block_changed[y][x] = False
    self.block_image[y][x] = hval
    return bgr2rgb(data)
  
  def paint_image(self, x0, y0, w, h, data):
    if not SWFScreen.paint_image(self, x0, y0, w, h, data): return False
    x0 -= self.x0
    y0 -= self.y0
    #assert w and h and 0 < x0+w and x0 < self.out_width and 0 < y0+h and y0 < self.out_height
    if self.scaling:
      (x0,y0,w,h) = (int(x0*self.scaling), int(y0*self.scaling),
                     int(w*self.scaling), int(h*self.scaling))
    x1 = upperbound((x0+w-1)/self.block_w+1, self.hblocks)
    y1 = upperbound((self.out_height-y0)/self.block_h+1, self.vblocks)
    x0 = lowerbound(x0/self.block_w, 0)
    y0 = lowerbound((self.out_height-(y0+h-1))/self.block_h, 0)
    for line in self.block_changed[y0:y1]:
      for x in xrange(x0, x1):
        line[x] = True
    return True
  

##################################################################

##  MovieOutputStream
##
class MovieOutputStream:

  """
  MovieOutputStream is an abstract class which produces
  some external representation of a movie (either to a file or to a display).
  This is used for generating SWF files or playing movies on the screen.
  """
  
  def __init__(self, info, debug=0):
    self.debug = debug
    self.info = info
    self.output_frames = 0
    self.cursor_image = None
    self.cursor_offset = None
    self.cursor_pos = None
    return

  def open(self):
    return
  
  def set_keyframe(self):
    return
  
  def paint_frame(self, (images, othertags, cursor_info)):
    if cursor_info:
      (cursor_image, cursor_pos) = cursor_info
      self.cursor_image = cursor_image or self.cursor_image
      self.cursor_pos = cursor_pos or self.cursor_pos
    return

  def next_frame(self):
    self.output_frames += 1
    return
  
  def close(self):
    if self.debug:
      print >>stderr, 'stream: close'
    return

  def write_mp3frames(self, frameid=None):
    return
  
  def preserve_frame(self):
    return None
  
  def recover_frame(self, img):
    raise NotImplementedError


##  SWFOutputStream
##
class SWFOutputStream(MovieOutputStream):

  """
  SWFOutputStream is a MovieOutputStream which produces a SWF file.
  """

  swf_version = None

  def __init__(self, info, debug=0):
    assert info.filename, 'Filename not specified!'
    MovieOutputStream.__init__(self, info, debug)
    self.info.set_swf_version(self.swf_version)
    self.writer = None
    self.cursor_depth = None
    self.cursor_pos0 = None
    return

  def open(self):
    MovieOutputStream.open(self)
    print >>stderr, 'Creating movie: %r: version=%d, size=%dx%d, framerate=%s, compression=%s' % \
          (self.info.filename, self.info.swf_version,
           self.info.width, self.info.height,
           self.info.framerate, self.info.compression)
    self.writer = SWFWriter(self.info.filename, self.swf_version,
                            (0,self.info.width*20, 0,self.info.height*20),
                            self.info.framerate, self.info.compression)
    # Write BGColor
    self.writer.start_tag()
    self.writer.writergb((255,255,255))
    self.writer.end_tag(9)
    # add mp3 header (if any)
    if self.info.mp3:
      # write SoundStreamHeader
      assert self.info.mp3.isstereo != None, 'mp3 isstereo is not set.'
      assert self.info.mp3.sample_rate != None, 'mp3 sample_rate is not set.'
      self.writer.start_tag()
      MP3_RATE = {11025:1, 22050:2, 44100:3}
      rate = MP3_RATE[self.info.mp3.sample_rate]
      self.writer.writeui8(rate << 2 | 2 | int(self.info.mp3.isstereo))
      self.writer.writeui8(rate << 2 | (2<<4) | 2 | int(self.info.mp3.isstereo))
      self.writer.writeui16(int(self.info.mp3.sample_rate / self.info.framerate))
      # the first seeksamples, mp3.seek_frame should be preformed in advance.
      self.writer.writeui16(self.info.mp3.seeksamples)
      self.writer.end_tag(18)
    # Make the movie unscalable.
    if not self.info.scalable:
      # add actionscript: Stage.scaleMode("noScale")
      self.writer.start_action()
      self.writer.do_action(0x96,7) # PushData, size= 1 (type) + len(data) + 1 (0x00)
      self.writer.writeui8(0x00) # String
      self.writer.writestring('Stage')
      self.writer.do_action(0x1c) # GetVariable
      self.writer.do_action(0x96, 11) # Push
      self.writer.writeui8(0x00) # String
      self.writer.writestring('scaleMode')
      self.writer.do_action(0x96, 9) # Push
      self.writer.writeui8(0x00) # String
      self.writer.writestring('noScale')
      self.writer.do_action(0x4f) # setMember
      self.writer.end_action()
    
    self.othertags = []
    return

  def write_mp3frames(self, frameid=None):
    # add mp3 frames (if any)
    if frameid == None:
      frameid = self.output_frames
    if self.info.mp3:
      t = (frameid+1) / self.info.framerate
      (nsamples, seeksamples, mp3frames) = self.info.mp3.get_frames_until(t)
      # SoundStreamBlock
      self.writer.start_tag()
      self.writer.writeui16(nsamples)
      self.writer.writeui16(seeksamples)
      self.writer.write(''.join(mp3frames))
      self.writer.end_tag(19)
    return

  def define_shape(self, w, h, data, alpha=False):
    if self.debug:
      print >>stderr, 'define_shape:', (w,h), len(data)
    self.writer.start_tag()
    image_id = self.writer.newid()
    self.writer.writeui16(image_id)
    self.writer.writeui8(5)             # fmt=5: 24bits color
    self.writer.writeui16(w)
    self.writer.writeui16(h)
    self.writer.write(zlib.compress(data))
    if alpha:
      # DefineBitsLossless2
      self.writer.end_tag(36, forcelong=True) # because of flashplayer's bug
    else:
      # DefineBitsLossless
      self.writer.end_tag(20, forcelong=True) # because of flashplayer's bug
    # DefineShape3
    self.writer.start_tag()
    shape_id = self.writer.newid()
    self.writer.writeui16(shape_id)
    self.writer.writerect((20, w*20+20, 20, h*20+20))
    self.writer.write_style(3, [(0x43,None,None,None,image_id,(20,20,None,None,0,0))], [])
    self.writer.write_shape(3, [(0,(20,20)),(1,(w*20,0)),(1,(0,h*20)),(1,(-w*20,0)),(1,(0,-h*20))], fillstyle=1)
    self.writer.end_tag(32)
    return shape_id

  def place_object2(self, shape_id, x, y, depth):
    if self.debug:
      print >>stderr, 'place_object2:', shape_id, (x,y), depth
    # PlaceObject2
    self.writer.start_tag()
    if shape_id:
      self.writer.writeui8(2|4)
      self.writer.writeui16(depth)
      self.writer.writeui16(shape_id)
    else:
      self.writer.writeui8(1|4)
      self.writer.writeui16(depth)
    self.writer.writematrix((None, None, None, None, x*20, y*20))
    self.writer.end_tag(26)
    return
  
  # remove shape object
  # if you leave objects on the screen, it gets verry slow.
  def remove_object(self, depth):
    if self.debug:
      print >>stderr, 'remove_object:', depth
    # RemoveObject2
    self.writer.start_tag()
    self.writer.writeui16(depth)
    self.writer.end_tag(28)
    return

  # paint cursor
  def paint_frame(self, (images, othertags, cursor_info)):
    MovieOutputStream.paint_frame(self, (images, othertags, cursor_info))
    self.othertags.extend(othertags)
    return

  def next_frame(self):
    MovieOutputStream.next_frame(self)
    # add other unknown tags
    for (tag, data) in self.othertags:
      self.writer.start_tag()
      self.writer.write(data)
      self.writer.end_tag(tag)
    # show cursor
    if self.cursor_pos:
      shape_id = None
      if self.cursor_image:
        (w, h, dx, dy, data) = self.cursor_image
        self.cursor_image = None
        self.cursor_offset = (dx, dy)
        shape_id = self.define_shape(w, h, data, alpha=True)
      # shape_id is set when the cursor is changed.
      if shape_id or (self.cursor_offset and self.cursor_pos and self.cursor_pos0 != self.cursor_pos):
        if shape_id:
          if self.cursor_depth:
            self.remove_object(self.cursor_depth)
          else:
            self.cursor_depth = CURSOR_DEPTH
        (x,y) = self.screen.adjust_cursor_pos(self.cursor_pos, self.cursor_offset)
        self.place_object2(shape_id, x, y, self.cursor_depth)
        self.cursor_pos0 = self.cursor_pos
    # ShowFrame
    self.writer.start_tag()
    self.writer.end_tag(1)
    self.othertags = []
    return

  def close(self):
    MovieOutputStream.close(self)
    self.writer.start_tag()
    self.writer.end_tag(0)
    self.writer.write_file(self.output_frames)
    return

  
##  SWFShapeStream
##
class SWFShapeStream(SWFOutputStream):

  """
  SWFShapeStream produces a SWF file with a set of overlapped
  shapes with lossless images.
  """
  
  swf_version = 5                       # SWF5

  def open(self):
    SWFOutputStream.open(self)
    (x,y,w,h) = self.info.clipping
    self.screen = SWFShapeScreen(x, y, w, h, scaling=self.info.scaling)
    self.set_keyframe()
    self.tmp_objs = []
    self.replaced = {}
    return

  # add shape object
  def add_object(self, img, depth, x, y):
    (w,h) = imgsize(img)
    data = convert_image_to_string_xrgb(img)
    self.place_object2(self.define_shape(w, h, data), x, y, depth)
    return

  def paint_frame(self, (images, othertags, cursor_info)):
    SWFOutputStream.paint_frame(self, (images, othertags, cursor_info))
    for ((x0,y0), (w,h,data)) in images:
      if self.debug:
        print >>stderr, 'paint:', (x0,y0), (w,h)
      if self.screen.paint_image(x0, y0, w, h, data):
        # do not attempt to create another shape object if
        # its entire area is already covered by other objects which are
        # going to be created.
        if self.info.scaling:
          (x0,y0,w,h) = (int(x0*self.info.scaling), int(y0*self.info.scaling),
                         int(w*self.info.scaling), int(h*self.info.scaling))
        self.screen.place_object(self.tmp_objs, x0, y0, w, h, self.replaced)
    return

  def next_frame(self):
    self.screen.prepare_image()
    addobjs = []
    for (depth,x0,y0,w,h) in self.tmp_objs:
      if depth in self.replaced:
        # if the object is completely covered by another object which is
        # placed within the same frame, do nothing.
        del self.replaced[depth]
      else:
        addobjs.append((depth,x0,y0,w,h))
    # Remove completely overriden objects.
    for depth in self.replaced.iterkeys():
      self.remove_object(depth)
    for (depth,x0,y0,w,h) in addobjs:
      # Image & Shape & Place tags.
      self.add_object(self.screen.get_image(x0, y0, w, h), depth, x0, y0)
    self.screen.next_frame()
    self.tmp_objs = []
    self.replaced = {}
    SWFOutputStream.next_frame(self)
    return
  
  def set_keyframe(self):
    self.screen.initmap()
    return
  

##  SWFVideoStream
##
class SWFVideoStream(SWFOutputStream):

  """
  SWFVideoStream produces a SWF file with a video object.
  """
  
  swf_version = 7                       # SWF7

  def open(self):
    SWFOutputStream.open(self)
    (x,y,w,h) = self.info.clipping
    self.screen = SWFVideoScreen(x, y, w, h, self.info.blocksize, self.info.blocksize,
                                 scaling=self.info.scaling)
    self.video_object = self.writer.newid()
    # write DefineVideoStream
    assert not self.writer.fpstack
    pos0 = self.writer.fp.tell()
    self.writer.start_tag()
    self.writer.writeui16(self.video_object) # video char
    self.mangle_pos = pos0 + 4
    # XXX:
    # Here we need to put the total number of the frames in this video object.
    # However, we don't know this for now. So we put a tentative number
    # and change it later on.
    self.writer.writeui16(0)            # must be changed later.
    self.writer.writeui16(self.screen.out_width)
    self.writer.writeui16(self.screen.out_height)
    self.writer.writeui8(0)             # smoothing off
    self.writer.writeui8(3)             # SCREENVIDEO
    self.writer.end_tag(60)
    self.place_object2(self.video_object, 0, 0, 1)
    self.set_keyframe()
    self.painted = False
    return

  def paint_frame(self, (images, othertags, cursor_info)):
    SWFOutputStream.paint_frame(self, (images, othertags, cursor_info))
    for ((x0,y0), (w,h,data)) in images:
      if self.debug:
        print >>stderr, 'paint:', (x0,y0), (w,h)
      if self.screen.paint_image(x0, y0, w, h, data):
        self.painted = True
    return

  def next_frame(self):
    if self.is_keyframe or self.painted:
      r = []
      changed = self.is_keyframe
      self.screen.prepare_image()
      for y in xrange(self.screen.vblocks):
        for x in xrange(self.screen.hblocks):
          data = self.screen.get_block_change(x, y)
          r.append(data)
          if data:
            changed = True
      if changed:
        # write VideoFrame tag
        self.writer.start_tag()
        self.writer.writeui16(self.video_object) # video char
        self.writer.writeui16(self.output_frames)
        # SCREENVIDEOPACKET
        if self.is_keyframe:
          self.writer.writebits(4, 1)
          self.is_keyframe = False
        else:
          self.writer.writebits(4, 2)
        self.writer.writebits(4, 3) # screenvideo codec
        self.writer.writebits(4, self.screen.block_w/16-1)
        self.writer.writebits(12, self.screen.out_width)
        self.writer.writebits(4, self.screen.block_h/16-1)
        self.writer.writebits(12, self.screen.out_height)
        self.writer.finishbits()
        for data in r:
          if data:
            data = zlib.compress(data)
            self.writer.writeub16(len(data))
            self.writer.write(data)
          else:
            self.writer.writeub16(0)
        self.writer.end_tag(61)
        # PlaceObject2
        # For some reason we need to set the RATIO to the current frame number every time.
        # This is not documented!
        self.writer.start_tag()
        self.writer.writeui8(17)
        self.writer.writeui16(self.video_object)
        self.writer.writeui16(self.output_frames)
        self.writer.end_tag(26)
    SWFOutputStream.next_frame(self)
    return

  def set_keyframe(self):
    self.screen.init_blocks()
    self.is_keyframe = True
    return

  def close(self):
    assert not self.writer.fpstack
    self.writer.fp.seek(self.mangle_pos) # mangle this
    self.writer.writeui16(self.output_frames) # set the number of frames into DefineVideoStream tag.
    self.writer.fp.seek(0, 2) # go back
    SWFOutputStream.close(self)
    return


##  ImageSequenceStream
##
class ImageSequenceStream(MovieOutputStream):
  
  def __init__(self, info, debug=0):
    import os.path
    MovieOutputStream.__init__(self, info, debug=debug)
    (root, ext) = os.path.splitext(info.filename)
    self.filename_template = '%s-%%05d%s' % (root, ext)
    return
  
  def open(self):
    (x,y,w,h) = self.info.clipping
    self.screen = SWFScreen(x, y, w, h, scaling=self.info.scaling)
    return
  
  def paint_frame(self, (images, othertags, cursor_info)):
    for ((x0,y0), (w,h,data)) in images:
      if self.debug:
        print >>stderr, 'paint:', (x0,y0), (w,h)
      self.screen.paint_image(x0, y0, w, h, data)
    if cursor_info:
      (cursor_image, cursor_pos) = cursor_info
      if cursor_image:
        (w, h, dx, dy, data) = cursor_image
        self.cursor_offset = (dx, dy)
        self.cursor_image = create_image_from_string_argb(w, h, data)
      if cursor_pos:
        self.cursor_pos = cursor_pos
    return

  def next_frame(self):
    fname = self.filename_template % self.output_frames
    if self.debug:
      print >>stderr, 'writing:', fname
    self.screen.prepare_image(self.cursor_image, self.cursor_offset, self.cursor_pos)
    self.screen.dump_image(fname)
    MovieOutputStream.next_frame(self)
    return


##  MPEGVideoStream
##  Contributed by Vincent Pelletier <subdino2004@yahoo.fr>
##
try:
  import pymedia
  from pymedia.video import vcodec
  #print >>stderr, 'Using pymedia', pymedia.__version__
except ImportError:
  vcodec = None
class MPEGVideoStream(MovieOutputStream):

  """
  MPEGVideoStream produces a MPEG file.
  """

  # Supported codecs: mpeg2video mpeg1video
  # Depending on installed codecs: h264 h263 mpeg4 msmpeg4v3 msmpeg4v2 msmpeg4v1 ...
  def __init__(self, info, codec='mpeg2video', debug=False):
    assert info.filename, 'Filename not specified!'
    MovieOutputStream.__init__(self, info, debug)
    self.mpeg_codec = codec
    return

  def open (self):
    MovieOutputStream.open(self)
    print >>stderr, 'Creating MPEG: %r: codec=%s, size=%dx%d, framerate=%s' % \
          (self.info.filename, self.mpeg_codec,
           self.info.width, self.info.height,
           self.info.framerate)

    (x,y,w,h) = self.info.clipping
    # Crop to match codec constraints
    w = w - w % 2 # width constraint : multiple of 2
    h = h - h % 2 # height constraint : multiple of 2
    self.screen = SWFScreen(x, y, w, h, scaling=self.info.scaling)
    params = {
      'type': 0,
      'gop_size': 12,
      'frame_rate_base': 125,
      'max_b_frames': 0,
      'height': self.screen.out_height,
      'width': self.screen.out_width,
      'frame_rate': 2997,
      'deinterlace': 0,
      'id':  vcodec.getCodecID(self.mpeg_codec),
      'format': vcodec.formats.PIX_FMT_YUV420P
      }
    params['frame_rate'] = int(params['frame_rate_base'] * self.info.framerate)
    if self.mpeg_codec == 'mpeg1video':
      params['bitrate'] = 2700000
    else:
      params['bitrate'] = 9800000
    if self.debug:
      print >>stderr, 'Setting codec to ', params
    self.encoder = vcodec.Encoder(params)
    self.out_file = open(self.info.filename, 'wb')
    return

  def paint_frame (self, (images, othertags, cursor_info)):
    MovieOutputStream.paint_frame(self, (images, othertags, cursor_info))
    for ((x0, y0), (w, h, data)) in images:
      if self.debug:
        print >>stderr, 'paint:', (x0,y0), (w,h)
      self.screen.paint_image(x0, y0, w, h, data)
    if cursor_info:
      (cursor_image, cursor_pos) = cursor_info
      if cursor_image:
        (w, h, dx, dy, data) = cursor_image
        self.cursor_offset = (dx, dy)
        self.cursor_image = create_image_from_string_argb(w, h, data)
      if cursor_pos:
        self.cursor_pos = cursor_pos
    return

  def next_frame (self):
    if self.debug:
      print >>stderr, 'prepare_image:', (self.screen.out_width, self.screen.out_height)
    img = self.screen.prepare_image(self.cursor_image, self.cursor_offset, self.cursor_pos)
    strFrame = convert_image_to_string_rgb(img)
    bmpFrame = vcodec.VFrame(vcodec.formats.PIX_FMT_RGB24,
                             (self.screen.out_width, self.screen.out_height),
                             (strFrame, None, None))
    yuvFrame = bmpFrame.convert(vcodec.formats.PIX_FMT_YUV420P)
    encFrame = self.encoder.encode(yuvFrame)
    self.out_file.write(encFrame.data)
    MovieOutputStream.next_frame(self)
    return

  def close (self):
    MovieOutputStream.close(self)
    self.out_file.close()
    return


##  FLVVideoStream
##  Contributed by Luis Fernando <lfkpoa-69@yahoo.com.br>
##
class FLVVideoStream(MovieOutputStream):

  """
  FLVVideoStream produces a FLV file with a video object.
  """
  
  flv_version = 1                       # FLV 1

  def __init__(self, info, debug=0):
    assert info.filename, 'Filename not specified!'
    MovieOutputStream.__init__(self, info, debug)
    self.info.set_swf_version(None)
    return
  
  def open(self):
    MovieOutputStream.open(self)
    self.writer = FLVWriter(self.info.filename, self.flv_version,
                            (0,self.info.width*20, 0,self.info.height*20),
                            self.info.framerate)
    self.othertags = []
    (x,y,w,h) = self.info.clipping
    self.screen = SWFVideoScreen(x, y, w, h, self.info.blocksize, self.info.blocksize,
                                 scaling=self.info.scaling)
    self.set_keyframe()
    return

  def paint_frame(self, (images, othertags, cursor_info)):
    MovieOutputStream.paint_frame(self, (images, othertags, cursor_info))
    self.othertags.extend(othertags)
    for ((x0,y0), (w,h,data)) in images:
      if self.debug:
        print >>stderr, 'paint:', (x0,y0), (w,h)
      self.screen.paint_image(x0, y0, w, h, data)
    if cursor_info:
      (cursor_image, cursor_pos) = cursor_info
      if cursor_image:
        (w, h, dx, dy, data) = cursor_image
        self.cursor_offset = (dx, dy)
        self.cursor_image = create_image_from_string_argb(w, h, data)
      if cursor_pos:
        self.cursor_pos = cursor_pos
    return

  def next_frame(self):
    r = []
    self.screen.prepare_image(self.cursor_image, self.cursor_offset, self.cursor_pos)
    for y in xrange(self.screen.vblocks):
      for x in xrange(self.screen.hblocks):
        r.append(self.screen.get_block_change(x, y))
    # write FLV tag
    self.writer.start_tag()
    # SCREENVIDEOPACKET
    if self.is_keyframe:
      self.writer.writebits(4, 1)
      self.is_keyframe = False
    else:
      self.writer.writebits(4, 2)
    self.writer.writebits(4, 3) # screenvideo codec
    self.writer.writebits(4, self.screen.block_w/16-1)
    self.writer.writebits(12, self.screen.out_width)
    self.writer.writebits(4, self.screen.block_h/16-1)
    self.writer.writebits(12, self.screen.out_height)
    self.writer.finishbits()
    for data in r:
      if data:
        data = zlib.compress(data)
        self.writer.writeub16(len(data))
        self.writer.write(data)
      else:
        self.writer.writeub16(0)
    # the first tag: always t == 0
    t = (self.output_frames*1000) / self.info.framerate
    self.writer.end_tag(9, t)
    MovieOutputStream.next_frame(self)
    return

  def set_keyframe(self):
    self.screen.init_blocks()
    self.is_keyframe = True
    return

  def close(self):
    assert not self.writer.fpstack
    MovieOutputStream.close(self)
    self.writer.write_file(self.output_frames)
    return


##  StreamFactory
##
def StreamFactory(type):
  return {
    'flv': FLVVideoStream,
    'swf5': SWFShapeStream,
    'swf7': SWFVideoStream,
    'mpeg': MPEGVideoStream,
    'image': ImageSequenceStream,
    }[type]


##  MovieBuilder
##
class MovieBuilder:

  """
  MovieBuilder arranges a set of partial images to construct
  a consistent image of each frame. It provides a proper sequence of images
  to a MovieOutputStream object.
  """

  # src: MovieContainer, stream: MovieOutputStream
  def __init__(self, movie, stream, kfinterval=0, mp3seek=False, verbose=True, pinterval=50, debug=0):
    self.movie = movie
    self.stream = stream
    self.debug = debug
    self.verbose = verbose
    self.mp3seek = mp3seek
    self.kfinterval = kfinterval
    self.pinterval = pinterval
    return

  def start(self):
    self.frameid = -1
    self.preserved = {}
    if self.movie.info.mp3:
      self.movie.info.mp3.seek_frame(0)
    self.stream.open()
    return
  
  def step(self):
    if self.debug:
      print >>stderr, 'step: %d -> %d' % (self.frameid, self.frameid+1)
    self.frameid += 1
    self.stream.paint_frame(self.movie.get_frame(self.frameid))
    if ((self.frameid % self.pinterval) == 0 and 
        self.frameid not in self.preserved):
      img = self.stream.preserve_frame()
      if img:
        self.preserved[self.frameid] = img
        if self.debug:
          print >>stderr, 'preserve: %d' % self.frameid
    return

  def seek(self, frameid):
    if self.debug:
      print >>stderr, 'seek: %d -> %d' % (self.frameid, frameid)
    if frameid == 0:
      self.frameid = -1
      self.step()
      if self.movie.info.mp3 and self.mp3seek:
        self.movie.info.mp3.seek_frame(0)
    elif frameid == self.frameid+1:
      self.step()
    else:
      if frameid < self.frameid:
        prev = 0
        image = None
        for (fid,img) in self.preserved.iteritems():
          if fid <= frameid and prev <= fid:
            (prev, image) = (fid, img)
        if image:
          self.stream.recover_frame(image)
          self.stream.set_keyframe()
      else:
        prev = self.frameid
      # replay the sequences.
      if self.debug:
        print >>stderr, 'range:', prev, frameid
      self.frameid = prev
      for fid in xrange(prev, frameid):
        self.step()
      if self.movie.info.mp3 and self.mp3seek:
        self.movie.info.mp3.seek_frame(frameid / self.movie.info.framerate)
    if self.kfinterval and (frameid % self.kfinterval) == 0:
      self.stream.set_keyframe()
    return
  
  def finish(self):
    return

  def build(self, frames=None):
    if not frames:
      frames = range(self.movie.nframes)
    self.start()
    for frameid in frames:
      self.seek(frameid)
      if self.debug:
        print >>stderr, 'next_frame'
      if self.verbose:
        stderr.write('.'); stderr.flush()
      if self.movie.info.mp3:
        if self.mp3seek:
          self.stream.write_mp3frames(frameid)
        else:
          self.stream.write_mp3frames()
      self.stream.next_frame()
    self.finish()
    if self.verbose:
      print >>stderr, '%d frames written (duration=%.1fs)' % \
            (len(frames), len(frames)/self.movie.info.framerate)
    return
