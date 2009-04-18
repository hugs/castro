pyvnc2swf
$Id: README.txt,v 1.33 2008/11/16 02:39:40 euske Exp $


For documentation, see docs/pyvnc2swf.html.


Homepage: http://www.unixuser.org/~euske/vnc2swf/
Discussion: http://lists.sourceforge.net/lists/listinfo/vnc2swf-users


Acknowledgements:
 * Jesse Ruderman (Seekbar javascript code)
 * Radoslaw Grzanka (MemoryError bug fix)
 * Luis Fernando Kauer (VNC protocol error fix, cursor pseudo-encoding support, FLV support, lots of bugfixes)
 * Rajesh Menon (OSX assertion error fix)
 * Vincent Pelletier (MPEG encoding support)
 * Uchida Yasuo (Windows file bug fix)
 * Andy Leszczynski (MP3 and PyMedia bug fix)
 * David Fraser (audio recording with PyMedia)

Bugs:
 * Noises with non-multiple scaling (e.g. 0.7)
 * Ctrl-C at bad timings might cause the program abort.
 * Sometimes MPEGVideoStream crashes. (pymedia? - I couldn't replay.)
 * Timing issue (esp. notable in vnclog)
 
TODOs:
 * Audio support on FLV.
 * Neat GUI.
 * Authoring tool. (combining vnc2swf.py, edit.py and play.py)
 * Cursor shadow support.
 * Improve image scaling. (specify the scale ratio by size)
 * Screen snapshot tool (with no animation).
 * Distribution of Windows/Mac binaries. (py2exe, py2app)
 * Audio recording/replay with PyMedia.
 * Stop recording remotely.
 * FLV editing.

$ x11vnc -quiet -cursor -viewonly -bg -localhost -nopw && ./vnc2swf.py -n -o out.swf :0

$ tcpserver -vRHl0 localhost 10000 sh -c 'x11vnc -quiet -bg -nopw -viewonly -localhost -cursor -wait 10 -defer 10 >/dev/null 2>&1 && echo HTTP/1.0 200 OK && echo Content-Type: video/x-flv && echo && ./vnc2swf.py -n -t flv -o -'
