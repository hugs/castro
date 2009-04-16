#!/usr/bin/env python
##
##  pyvnc2swf - vnc2swf.py
##
##  $Id: vnc2swf.py,v 1.7 2008/11/16 02:39:40 euske Exp $
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

import sys, os, os.path, time, socket, re
import Tkinter, tkFileDialog, tkMessageBox, tempfile, shutil
from tkSimpleDialog import Dialog
from struct import pack, unpack
import threading

from movie import SWFInfo
from output import StreamFactory
from rfb import RFBError, RFBNetworkClient, RFBFileParser, RFBNetworkClientForRecording, RFBStreamConverter
stderr = sys.stderr


##  tkPasswordDialog
##
class tkPasswordDialog(Dialog):

  def __init__(self, title, prompt, master=None):
    if not master:
      master = Tkinter._default_root
    self.prompt = prompt
    Dialog.__init__(self, master, title)
    return
  
  def destroy(self):
    self.entry = None
    Dialog.destroy(self)
    return
  
  def body(self, master):
    w = Tkinter.Label(master, text=self.prompt, justify=Tkinter.LEFT)
    w.grid(row=0, padx=5, sticky=Tkinter.W)
    self.entry = Tkinter.Entry(master, name="entry", show="*")
    self.entry.grid(row=1, padx=5, sticky=Tkinter.W+Tkinter.E)
    return self.entry
  
  def validate(self):
    self.result = self.entry.get()
    return 1


##  tkEntryDialog
##
class tkEntryDialog(Dialog):

  def __init__(self, title, prompt, pattern=None, default=None, master=None):
    if not master:
      master = Tkinter._default_root
    self.prompt = prompt
    self.default = default
    self.pattern = re.compile(pattern)
    Dialog.__init__(self, master, title)
    return
  
  def destroy(self):
    self.entry = None
    Dialog.destroy(self)
    return
  
  def body(self, master):
    w = Tkinter.Label(master, text=self.prompt, justify=Tkinter.LEFT)
    w.grid(row=0, padx=5, sticky=Tkinter.W)
    self.entry = Tkinter.Entry(master, name="entry")
    self.entry.grid(row=1, padx=5, sticky=Tkinter.W+Tkinter.E)
    if self.default:
      self.entry.insert(0, self.default)
    return self.entry
  
  def validate(self):
    self.result = self.entry.get()
    if self.pattern and not self.pattern.match(self.result):
      return 0
    return 1


##  RFBNetworkClientWithTkMixin
##
class RFBNetworkClientWithTkMixin:

  def tk_init(self, root):
    self.root = root
    self.doloop = True
    return

  def interrupt(self):
    self.doloop = False
    return

  def loop(self):
    self.doloop = True
    while self.doloop:
      self.root.update()
      if not self.loop1(): break
    self.finish_update()
    return self

  def getpass(self):
    return tkPasswordDialog('Login',
                            'Password for %s:%d' % (self.host, self.port),
                            self.root).result

class RFBNetworkClientWithTk(RFBNetworkClientWithTkMixin, RFBNetworkClient): pass
class RFBNetworkClientForRecordingWithTk(RFBNetworkClientWithTkMixin, RFBNetworkClientForRecording): pass


##  VNC2SWFWithTk
##
class VNC2SWFWithTk:

  FILE_TYPES = [
    ('Flash(v5)', 'swf5',  'Macromedia Flash Files', '.swf'),    # 0
    ('Flash(v7)', 'swf7',  'Macromedia Flash Files', '.swf'),    # 1
    ('FLV',       'flv',   'Macromedia Flash Video Files', '.flv'), # 3
    ('MPEG',      'mpeg',  'MPEG Files', '.mpeg'),               # 2
    ('VNCRec',    'vnc',   'VNCRec Files', '.vnc'),              # 4
    ]

  def __init__(self, tempdir, info,
               outtype='swf5', host='localhost', port=5900,
               preferred_encoding=(0,), subprocess=None, pwdfile=None,
               debug=0):
    self.tempdir = tempdir
    self.moviefile = info.filename
    self.info = info
    self.debug = debug
    self.preferred_encoding = preferred_encoding
    self.subprocess = subprocess
    self.pwdfile = pwdfile
    self.outtype = outtype
    self.host = host
    self.port = port
    self.recording = False
    self.exit_immediately = False
    self.root = Tkinter.Tk()
    self.root.title('vnc2swf.py')
    self.root.wm_protocol('WM_DELETE_WINDOW', self.file_exit)
    self.toggle_button = Tkinter.Button(master=self.root)
    self.toggle_button.pack(side=Tkinter.LEFT)
    self.status_label = Tkinter.Label(master=self.root, justify=Tkinter.LEFT)
    self.status_label.pack(side=Tkinter.LEFT)
    self.setup_menubar()
    self.file_new(True)
    return

  def frames(self):
    return self.stream and self.stream.output_frames

  # Set up the GUI components.
  def setup_menubar(self):
    
    def option_server():
      x = tkEntryDialog('Server', 'Server? (host:port)', pattern='^([^:/]+(:\d+)?|)$',
                        default='%s:%d' % (self.host, self.port), master=self.root).result
      if not x: return
      m = re.match(r'^([^:/]*)(:(\d+))?', x)
      if not m:
        tkMessageBox.showerror('Invalid address: %s' % x)
        return
      (host, port) = (m.group(1) or 'localhost', int(m.group(3) or '5900'))
      if host != self.host or port != self.port and self.file_new_ask():
        (self.host, self.port) = (host, port)
        self.file_new(True)
      return

    def option_framerate():
      x = tkEntryDialog('Framerate', 'Framerate? (fps)', pattern='^([1-9][.0-9]+|)$',
                        default=self.info.framerate, master=self.root).result
      if not x: return
      framerate = float(x)
      if framerate != self.info.framerate and self.file_new_ask():
        self.info.framerate = framerate
        self.file_new(True)
      return

    def option_clipping():
      try:
        s = self.info.get_clipping()
      except ValueError:
        s = ''
      x = tkEntryDialog('Clipping', 'Clipping? (ex. 640x480+0+0)',
                        pattern='^(\d+x\d+\+\d+\+\d+|)$',
                        default=s, master=self.root).result
      if not x: return
      if x != s and self.file_new_ask():
        self.info.set_clipping(x)
        self.file_new(True)
      return

    record_type = Tkinter.StringVar(self.root)
    record_type.set(self.outtype)
    def option_type():
      if record_type.get() != self.outtype and self.file_new_ask():
        self.outtype = record_type.get()
        self.file_new()
      else:
        record_type.set(self.outtype)
      return

    menubar = Tkinter.Menu(self.root)
    self.file_menu = Tkinter.Menu(menubar, tearoff=0)
    self.file_menu.add_command(label="New...", underline=0, command=self.file_new, accelerator='Alt-N')
    self.file_menu.add_command(label="Save as...", underline=0, command=self.file_saveas, accelerator='Alt-S')
    self.file_menu.add_separator()
    self.file_menu.add_command(label="Exit", underline=1, command=self.file_exit)
    self.option_menu = Tkinter.Menu(menubar, tearoff=0)
    self.option_menu.add_command(label="Server...", underline=0, command=option_server)
    self.option_menu.add_command(label="Clipping...", underline=0, command=option_clipping)
    self.option_menu.add_command(label="Framerate...", underline=0, command=option_framerate)
    type_submenu = Tkinter.Menu(self.option_menu, tearoff=0)
    for (k,v,_,_) in self.FILE_TYPES:
      type_submenu.add_radiobutton(label=k, value=v, variable=record_type, command=option_type)
    self.option_menu.add_cascade(label="Type", underline=0, menu=type_submenu)
    menubar.add_cascade(label="File", underline=0, menu=self.file_menu)
    menubar.add_cascade(label="Option", underline=0, menu=self.option_menu)
    self.root.config(menu=menubar)
    self.root.bind('<Alt-n>', lambda e: self.file_new())
    self.root.bind('<Alt-s>', lambda e: self.file_saveas())
    return

  # Change the current status of UI.
  def set_status(self):
    
    def enable_menus(state):
      self.file_menu.entryconfig(0, state=state) # "File->New..."
      self.option_menu.entryconfig(0, state=state) # "Option->Server..."
      self.option_menu.entryconfig(1, state=state) # "Option->Clipping..."
      self.option_menu.entryconfig(2, state=state) # "Option->Framerate..."
      self.option_menu.entryconfig(3, state=state) # "Option->Type"
      return

    # "File->Save As..."
    if not self.recording and self.frames():
      self.file_menu.entryconfig(1, state='normal')
    else:
      self.file_menu.entryconfig(1, state='disabled')
    
    s = []
    if not self.recording:
      s.append('Ready (%d frames recorded).' % (self.frames() or 0))
      self.toggle_button.config(text='Start', underline=0)
      self.toggle_button.config(background='#80ff80', activebackground='#00ff00')
      self.toggle_button.config(command=self.record)
      self.root.bind('<s>', lambda e: self.record())
      self.root.bind('<space>', lambda e: self.record())
      enable_menus('normal')
    else:
      s.append('Recording.')
      self.toggle_button.config(text='Stop', underline=0)
      self.toggle_button.config(background='#ff8080', activebackground='#ff0000')
      self.toggle_button.config(command=self.client.interrupt)
      self.root.bind('<s>', lambda e: self.client.interrupt())
      self.root.bind('<space>', lambda e: self.client.interrupt())
      enable_menus('disabled')
    if self.host != 'localhost' or self.port != 5900:
      s.append('Server: %s:%d' % (self.host, self.port))
    if self.info.clipping:
      s.append('Clipping: %s' % self.info.get_clipping())
    if self.info.framerate:
      s.append('Framerate: %s' % self.info.framerate)
    self.status_label.config(text='\n'.join(s))
    return

  # File->New
  def file_new_ask(self):
    if self.frames():
      if not tkMessageBox.askokcancel('New file', 'Discard the current session?'):
        return False
    return True
  
  def file_new(self, force=False):
    if self.recording or (not force and not self.file_new_ask()): return
    ext = dict([ (t,ext) for (_,t,desc,ext) in self.FILE_TYPES ])[self.outtype]
    if self.moviefile:
      moviefile = self.moviefile
    else:
      moviefile = os.path.join(self.tempdir, 'pyvnc2swf-%d%s' % (os.getpid(), ext))
    self.info.filename = moviefile
    self.fp = None
    if self.outtype == 'vnc':
      self.fp = file(self.info.filename, 'wb')
      self.client = RFBNetworkClientForRecordingWithTk(
        self.host, self.port, self.fp, pwdfile=self.pwdfile,
        preferred_encoding=self.preferred_encoding)
      self.stream = None
    else:
      self.stream = StreamFactory(self.outtype)(self.info)
      self.client = RFBNetworkClientWithTk(
        self.host, self.port, RFBStreamConverter(self.info, self.stream),
        pwdfile=self.pwdfile,
        preferred_encoding=self.preferred_encoding)
    self.set_status()
    return True
    
  # File->SaveAs
  def file_saveas(self):
    if self.recording or not self.frames(): return
    (ext,desc) = dict([ (t,(ext,desc)) for (_,t,desc,ext) in self.FILE_TYPES ])[self.outtype]
    filename = tkFileDialog.asksaveasfilename(
      master=self.root, title='Vnc2swf Save As', defaultextension=ext,
      filetypes=[(desc,'*'+ext), ("All Files", "*")]
      )
    if not filename: return
    if self.stream:
      # Finish the movie.
      self.stream.close()
      self.stream = None
      if self.fp:
        self.fp.close()
        self.fp = None
    shutil.move(self.info.filename, filename)
    self.info.write_html(filename=filename)
    self.set_status()
    return

  # File->Exit
  def file_exit(self):
    if self.recording:
      self.client.interrupt()
      self.exit_immediately = True
    else:
      if self.frames():
        if not tkMessageBox.askokcancel('Exit', 'Discard the current session?'):
          return
      self.root.destroy()
    return
  
  # Do recording.
  def record(self):
    self.client.tk_init(self.root)
    try:
      self.client.init().auth().start()
    except socket.error, e:
      return self.error('Socket error', e)
    except RFBError, e:
      return self.error('RFB protocol error', e)
    if self.debug:
      print >>stderr, 'start recording'
    self.recording = True
    self.set_status()
    if self.subprocess:
      self.subprocess.start()
    try:
      self.client.loop()
    except socket.error, e:
      return self.error('Socket error', e)
    except RFBError, e:
      return self.error('RFB protocol error', e)
    if self.debug:
      print >>stderr, 'stop recording'
    if self.subprocess:
      self.subprocess.stop()
    self.client.close()
    self.recording = False
    self.set_status()
    if self.exit_immediately:
      self.file_exit()
    return

  # Displays an error message.
  def error(self, msg, arg):
    print >>stderr, arg
    tkMessageBox.showerror('vnc2swf: %s' % msg, str(arg))
    return

  # Runs Tk mainloop.
  def run(self):
    self.root.mainloop()
    return


##  vnc2swf - CLI routine
##
def vnc2swf(info, outtype='swf5', host='localhost', port=5900, 
            preferred_encoding=(0,), subprocess=None, pwdfile=None, vncfile=None,
            debug=0, merge=False):
  fp = None
  if outtype == 'vnc':
    if info.filename == '-':
      fp = sys.stdout
    else:
      fp = file(info.filename, 'wb')
    client = RFBNetworkClientForRecording(host, port, fp, pwdfile=pwdfile,
                                          preferred_encoding=preferred_encoding, debug=debug)
  else:
    stream = StreamFactory(outtype)(info, debug=debug)
    converter = RFBStreamConverter(info, stream, debug=debug)
    if vncfile:
      client = RFBFileParser(vncfile, converter, debug=debug)
    else:
      client = RFBNetworkClient(host, port, converter, pwdfile=pwdfile,
                                preferred_encoding=preferred_encoding, debug=debug)
  try:
    client.init().auth().start()
  except socket.error, e:
    print >>stderr, 'Socket error:', e
  except RFBError, e:
    print >>stderr, 'RFB error:', e
  if debug:
    print >>stderr, 'start recording'
  if subprocess:
    subprocess.start()
  try:
    client.loop()
  except KeyboardInterrupt:
    pass
  except socket.error, e:
    print >>stderr, 'Socket error:', e
  except RFBError, e:
    print >>stderr, 'RFB error:', e
  if debug:
    print >>stderr, 'stop recording'
  if subprocess:
    subprocess.stop()
  client.close()
  stream.close()
  info.write_html()
  if fp:
    fp.close()
  # Contributed by David Fraser
  if merge:
    tmpfile = os.tempnam(os.path.dirname(info.filename), "vncmerge-") + os.path.basename(info.filename)
    print >>stderr, "renaming %s to %s for merge" % (info.filename, tmpfile)
    if os.path.exists(tmpfile):
      os.remove(tmpfile)
    os.rename( info.filename, tmpfile )
    try:
      # TODO: sort out getting outputfilename properly
      audiofilename = subprocess.outputfile
      import edit
      args = ["-d", "-o", info.filename, "-a", audiofilename, tmpfile]
      if not edit.main(args):
        print >>stderr, "Error doing merge..."
    finally:
      origexists, tmpexists = os.path.exists(info.filename), os.path.exists(tmpfile)
      print >>stderr, "origexists %r, tmpexists %r" % (origexists, tmpexists)
      if origexists and tmpexists:
        try:
          os.remove(tmpfile)
        except OSError, e:
          print >>stderr, "Could not remove temporary file: %s" % e
      elif tmpexists:
        print >>stderr, "only tmpfile remains after merge, renaming to original (but will not contain sound)"
        os.rename( tmpfile, info.filename )
  return


# Thread management
class RecordingThread:
  def __init__(self, outputfile):
    try:
      import record_sound
    except ImportError, e:
      print >>stderr, "unable to use pymedia?:", e
      raise
    self.outputfile = outputfile
    self.recorder = record_sound.voiceRecorder(self.outputfile)
    self.thread = threading.Thread(target=self.recorder.run)

  def start(self):
    self.thread.start()

  def stop(self):
    self.recorder.finished = True
    self.thread.join()

# Subprocess management
class Subprocess:
  
  def __init__(self, s):
    try:
      import subprocess
    except ImportError:
      print >>stderr, '-S option requires Python 2.4 or newer.'
      sys.exit(111)
    if not hasattr(os, 'kill'):
      print >>stderr, '-S option works only on Unix or Mac OS X.'
      sys.exit(111)
    self.args = s.split(' ')
    self.popen = None
    return
  
  def start(self):
    import subprocess
    self.popen = subprocess.Popen(self.args)
    return
  
  def stop(self):
    import signal
    os.kill(self.popen.pid, signal.SIGINT)
    self.popen.wait()
    return


# main
# ./vnc2swf.py -S 'arecord -t wav -c 1 -r 22050 out.wav' -n -o out.swf 
def main(argv):
  import getopt
  def usage():
    print ('usage: %s [-d] [-n] [-o filename] [-t {flv|mpeg|swf5|swf7|vnc}]'
           ' [-e encoding] [-N] [-C clipping] [-r framerate] [-s scaling] [-z] [-m] [-a] [-V]'
           ' [-S subprocess] [-P pwdfile] [host[:display] [port]]' % argv[0])
    return 100
  try:
    (opts, args) = getopt.getopt(argv[1:], 'dno:t:e:NC:r:S:P:s:zmaV')
  except getopt.GetoptError:
    return usage()
  (debug, console, outtype, subprocess, merge, pwdfile, isfile) = (0, False, None, None, False, None, False)
  (cursor, host, port, preferred_encoding) = (True, 'localhost', 5900, (0,))
  info = SWFInfo()
  for (k, v) in opts:
    if k == '-d': debug += 1
    elif k == '-n': console = True
    elif k == '-t': outtype = v
    elif k == '-e': preferred_encoding = tuple([ int(i) for i in v.split(',') ])
    elif k == '-N': cursor = False
    elif k == '-S': subprocess = Subprocess(v)
    elif k == '-a': subprocess = RecordingThread(v)
    elif k == '-m': merge = True
    elif k == '-P': pwdfile = v
    elif k == '-V': isfile = True
    elif k == '-o':
      info.filename = v
    elif k == '-C':
      try:
        info.set_clipping(v)
      except ValueError:
        print 'Invalid clipping specification:', v
        return usage()
    elif k == "-r":
      info.framerate = int(v)
    elif k == "-z":
      info.set_scalable(True)
    elif k == '-s':
      info.scaling = float(v)
      assert 0 < info.scaling and info.scaling <= 1.0, 'Invalid scaling.'
  if not outtype:
    if info.filename:
      if info.filename.endswith('.vnc'):
        outtype = 'vnc'
      elif info.filename.endswith('.swf'):
        outtype = 'swf5'
      elif info.filename.endswith('.mpg') or info.filename.endswith('.mpeg'):
        outtype = 'mpeg'
      elif info.filename.endswith('.flv'):
        outtype = 'flv'
    else:
      outtype = 'swf5'
  if outtype not in ('swf5','swf7','vnc','mpeg','flv'):
    print 'Please specify the output type or file extension.'
    return usage()
  if cursor:
    preferred_encoding += (-232,-239,)
  if 1 <= len(args):
    if ':' in args[0]:
      i = args[0].index(':')
      host = args[0][:i] or 'localhost'
      port = int(args[0][i+1:])+5900
    else:
      host = args[0]
  if 2 <= len(args):
    port = int(args[1])
  if console:
    if not info.filename:
      print 'Please specify the output filename.'
      return usage()
    vncfile = None
    if isfile:
      vncfile = sys.stdin
      if args:
        vncfile = file(args[0], 'rb')
    vnc2swf(info, outtype, host, port,
            preferred_encoding=preferred_encoding,
            subprocess=subprocess, pwdfile=pwdfile, vncfile=vncfile,
            merge=merge, debug=debug)
  else:
    tempdir = os.path.join(tempfile.gettempdir(), 'pyvnc2swf')
    try:
      os.mkdir(tempdir)
    except OSError:
      pass
    VNC2SWFWithTk(tempdir, info, outtype, host, port,
                  preferred_encoding=preferred_encoding,
                  subprocess=subprocess, pwdfile=pwdfile,
                  debug=debug).run()
  return

if __name__ == "__main__": sys.exit(main(sys.argv))
