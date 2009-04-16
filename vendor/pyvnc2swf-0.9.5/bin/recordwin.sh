#!/bin/sh
##
##  recordwin.sh
##  $Id: recordwin.sh,v 1.3 2008/11/16 02:39:40 euske Exp $
##
##  Quick recording script for UNIX.
##
##  usage:
##     recordwin.sh [-display disp] [-name winname] [-id winid] output.swf
##
##  Requires: x11vnc, xwininfo, awk
##

PYTHON=python
VNC2SWF=pyvnc2swf/vnc2swf.py
X11VNC=x11vnc
XWININFO=xwininfo
AWK=awk

usage() {
    echo "usage: $0 [-all] [-display display] [-name windowname] [-id windowid] [-type filetype] outfile"
    exit 100
}

vncopts=
xwopts=
desktop=
display="$DISPLAY"
while [ $# -gt 1 ]; do
    case "$1" in
	-all|-a) desktop=1;;
	-name) shift; xwopts="$xwopts -name $1";;
	-id) shift; xwopts="$xwopts -id $1";;
	-display|-d) shift; display="$1"; xwopts="$xwopts -display $1";;
	-type|-t) shift; vncopts="$vncopts -t $1";;
	-*) usage;;
    esac
    shift
done

if [ $# -lt 1 ]; then usage; fi

outfile="$1"
if [ "X$desktop" = "X" ]; then
  info=`$XWININFO $xwopts 2>/dev/null`
  if [ "X$info" = "X" ]; then
    echo "Window $xwopts not found!"
    exit 2
  fi
  geometry="-C `echo "$info" |
               $AWK '/Absolute upper-left X:/{x=$4}
                     /Absolute upper-left Y:/{y=$4}
                     /Width:/{w=$2} /Height:/{h=$2}
                     END {printf "%dx%d+%d+%d",w,h,x,y}' `"
  echo $geometry
fi

# launch x11vnc and vnc2swf
$X11VNC -quiet -bg -nopw -display "$display" -viewonly -localhost -cursor -wait 10 -defer 10 &&
  $PYTHON $VNC2SWF -n $vncopts -o "$outfile" $geometry
