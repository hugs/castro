#!/usr/bin/env python
##
##  pyvnc2swf - play.py
##
##  $Id: play.py,v 1.6 2008/11/16 02:39:40 euske Exp $
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

import sys, os.path, subprocess
import pygame
from image import create_image_from_string_argb
from movie import SWFInfo, MovieContainer
from output import SWFScreen, MovieOutputStream, MovieBuilder
lowerbound = max
upperbound = min
stderr = sys.stderr


##  PygameMoviePlayer
##
class PygameMoviePlayer(MovieOutputStream):

  """
  A simple movie player using Pygame.
  """

  font_size = 24

  def __init__(self, movie, debug=0):
    MovieOutputStream.__init__(self, movie.info, debug)
    self.builder = MovieBuilder(movie, self, debug)
    self.movie = movie
    return

  # MovieOuputStream methods
  
  def open(self):
    MovieOutputStream.open(self)
    # open window
    (x,y,w,h) = self.info.clipping
    self.imagesize = ( int(w*(self.info.scaling or 1)), int(h*(self.info.scaling or 1)) )
    self.screen = SWFScreen(x, y, w, h)
    (self.winwidth, self.winheight) = self.imagesize
    self.font = pygame.font.SysFont(pygame.font.get_default_font(), self.font_size)
    (fw1,fh1) = self.font.size('00000  ')
    (fw2,fh2) = self.font.size('[>]  ')
    self.panel_x0 = 0
    self.panel_x1 = fw1
    self.panel_x2 = fw1+fw2
    self.panel_y0 = self.winheight
    self.panel_y1 = self.winheight + fh1/2
    self.panel_h = fh1
    self.panel_w = lowerbound(64, self.winwidth-fw1-fw2-4)
    self.slide_h = fh1/2
    self.slide_w = 8
    self.actualwidth = self.panel_w+fw1+fw2+4
    pygame.display.set_caption(self.info.filename, self.info.filename)
    self.window = pygame.display.set_mode((self.actualwidth, self.winheight+self.panel_h))
    self.cursor_image = None
    self.cursor_pos = None
    self.playing = True
    self.mp3_out = self.mp3_dec = None
    #import pymedia
    #self.mp3_out = subprocess.Popen(['mpg123','-q','-'], stdin=subprocess.PIPE)
    #self.mp3_dec = pymedia.audio.acodec.Decoder('mp3')
    #self.mp3_out = pymedia.audio.sound.Output(44100,2,pymedia.audio.sound.AFMT_S16_LE)
    return

  def paint_frame(self, (images, othertags, cursor_info)):
    for ((x0,y0), (w,h,data)) in images:
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

  def preserve_frame(self):
    img = pygame.Surface(self.screen.buf.get_size())
    img.blit(self.screen.buf, (0,0))
    return img

  def recover_frame(self, img):
    self.screen.buf.blit(img, (0,0))
    return

  # additional methods

  def show_status(self):
    f = self.current_frame
    n = self.movie.nframes
    s = '%05d' % f
    self.window.fill((0,0,0), (0, self.panel_y0, self.actualwidth, self.panel_h))
    self.window.blit(self.font.render(s, 0, (255,255,255)), (0, self.panel_y0))
    if self.playing:
      self.window.blit(self.font.render('[>]', 0, (0,255,0)), (self.panel_x1, self.panel_y0))
    else:
      self.window.blit(self.font.render('[||]', 0, (255,0,0)), (self.panel_x1, self.panel_y0))
    self.window.fill((255,255,255), (self.panel_x2, self.panel_y1, self.panel_w, 1))
    x = self.panel_x2 + self.panel_w*f/n - self.slide_w/2
    y = self.panel_y1 - self.slide_h/2
    self.window.fill((255,255,255), (x, y, self.slide_w, self.slide_h))
    return

  def update(self):
    surface = self.screen.buf
    if self.info.scaling:
      # rotozoom is still very unstable... it sometime causes segfault :(
      # in case it doesn't work, use scale instead.
      #   surface = pygame.transform.scale(surface, self.imagesize)
      #   surface.set_alpha()
      surface = pygame.transform.rotozoom(surface, 0, self.info.scaling)
    self.window.blit(surface, (0,0))
    if self.cursor_image and self.cursor_pos:
      (x, y) = self.cursor_pos
      (dx, dy) = self.cursor_offset
      self.window.blit(self.cursor_image, (x-dx, y-dy))
    self.show_status()
    pygame.display.update()
    if self.mp3_out and self.info.mp3:
      t = (self.current_frame+1) / self.info.framerate
      (nsamples, seeksamples, mp3frames) = self.info.mp3.get_frames_until(t)
      r = self.mp3_dec.decode(''.join(mp3frames))
      self.mp3_out.play(r.data)
    return

  def toggle_playing(self):
    self.playing = not self.playing
    if self.playing and self.movie.nframes-1 <= self.current_frame:
      self.current_frame = 0
    return

  def seek(self, goal):
    self.current_frame = upperbound(lowerbound(goal, 0), self.movie.nframes-1)
    self.builder.seek(self.current_frame)
    self.playing = False
    self.update()
    return

  def play(self):
    drag = False
    loop = True
    ticks0 = 0
    self.current_frame = 0
    self.builder.start()
    while loop:
      if self.playing:
        events = pygame.event.get()
      else:
        events = [pygame.event.wait()]
      for e in events:
        if e.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION):
          (x,y) = e.pos
          if (e.type == pygame.MOUSEBUTTONDOWN and y < self.panel_y0):
            # the screen clicked
            self.toggle_playing()
          elif (self.panel_y0 < y and (e.type == pygame.MOUSEBUTTONDOWN or drag)):
            # slide bar dragging
            drag = True
            (x,y) = e.pos
            self.seek((x-self.panel_x2)*self.movie.nframes/self.panel_w)
        elif e.type == pygame.MOUSEBUTTONUP:
          drag = False
        elif e.type == pygame.KEYDOWN:
          if e.key in (13, 32): # space or enter
            self.toggle_playing()
          elif e.key in (113, 27): # 'q'uit, esc
            loop = False
          elif e.key in (115, 83): # 's'napshot
            (root, ext) = os.path.splitext(self.info.filename)
            fname = '%s-%05d.bmp' % (root, self.current_frame)
            pygame.image.save(self.screen.buf, fname)
            print >>stderr, 'Save:', fname
          elif e.key == 275: # right
            self.current_frame += 1
            self.seek(self.current_frame)
          elif e.key == 276: # left
            self.current_frame -= 1
            self.seek(self.current_frame)
          else:
            print >>stderr, 'Unknown key:', e
        elif e.type == pygame.QUIT:
          # window close attmpt
          loop = False
      if self.playing:
        self.builder.seek(self.current_frame)
        if self.movie.nframes-1 <= self.current_frame:
          # reach the end.
          self.playing = False
        else:
          self.current_frame += 1
          ticks1 = pygame.time.get_ticks()
          d = lowerbound(int(1000.0/self.info.framerate), ticks0-ticks1)
          ticks0 = ticks1
          pygame.time.wait(d)
        self.update()
      # loop end
    self.builder.finish()
    self.close()
    return
  

# play
def play(moviefiles, info, debug=0):
  movie = MovieContainer(info)
  for fname in moviefiles:
    if fname.endswith('.swf'):
      # vnc2swf file
      movie.parse_vnc2swf(fname, True, debug=debug)
    elif fname.endswith('.flv'):
      # flv file
      movie.parse_flv(fname, True, debug=debug)
    elif fname.endswith('.vnc'):
      # vncrec file
      movie.parse_vncrec(fname, debug=debug)
    else:
      raise ValueError('unsupported format: %r' % fname)
    info.filename = os.path.basename(fname)
  PygameMoviePlayer(movie, debug=debug).play()
  return

# main
def main(argv):
  import getopt, re
  def usage():
    print 'usage: %s [-d] [-r framerate] [-C WxH+X+Y] [-s scaling] file1 file2 ...' % argv[0]
    return 100
  try:
    (opts, args) = getopt.getopt(argv[1:], 'dr:C:s:')
  except getopt.GetoptError:
    return usage()
  #
  debug = 0
  info = SWFInfo()
  for (k, v) in opts:
    if k == '-d':
      debug += 1
    elif k == '-r':
      info.set_framerate(float(v))
    elif k == '-C':
      m = re.match(r'^(\d+)x(\d+)\+(\d+)\+(\d+)$', v)
      if not m:
        print >>stderr, 'Invalid clipping specification:', v
        return usage()
      x = map(int, m.groups())
      info.clipping = (x[2],x[3], x[0],x[1])
    elif k == '-s':
      info.scaling = float(v)
  if not args:
    print >>stderr, 'Specify at least one input movie.'
    return usage()
  return play(args, info, debug=debug)

if __name__ == "__main__": sys.exit(main(sys.argv))
