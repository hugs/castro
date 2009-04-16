#!/usr/bin/env python
##
##  pyvnc2swf - seekbar.py
##
##  $Id: html_templates.py,v 1.2 2008/11/15 10:07:09 euske Exp $
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

import sys, os, os.path
from swf import SWFParser

PYVNC2SWF_VERSION = '0.9.2'


##  Acknowledgement:
##
##    The following javascript code is contributed by Jesse Ruderman
##    (http://www.squarefree.com/). He kindly gave us permission to
##    release his code under GPL. Thank you, Jesse!
##

# seekbar header
SEEKBAR_HEADER = """
<script language="javascript">
/* Jesse Ruderman
 * July 18, 2004
 *
 * Remaining problems:
 *   IE sometimes crashes on exit after using the this script.
 *   In IE, it is a little ugly because IE doesn't support border-radius.
 *   In IE, it does not work at standalone Flash URLs.
 */

function setupSeekBar() {

setTimeout(initFlashControls, 100);

function initFlashControls()
{
  var count = 0;

  function tt(elem)
  {
    if (typeof elem.TotalFrames != "undefined") /* do not coerce elem.StopPlay to bool, because that breaks IE */
    {
      addFlashControls(elem);
      ++count;
    }
  }

  var i, x;

  for (i = 0; x = document.getElementsByTagName("object")[i]; ++i)
    tt(x);

  for (i = 0; x = document.getElementsByTagName("embed")[i]; ++i)
    tt(x);

}


function addFlashControls(flash)
{
  var controlsDiv = document.createElement("div");

  /* Put the controls under the Flash. 
   *
   * If the Flash is an <embed> in an <object>, we do not want to touch the <object>, because that would make
   * Mozilla re-test whether the <object> is broken and reset the <embed>.  So in that case, we put the controls
   * under the <object>.
   */
  var where = flash;
  while (where.parentNode.tagName.toLowerCase() == "object")
    where = where.parentNode;
  where.parentNode.insertBefore(controlsDiv, where.nextSibling);

  /* Construct controls using DOM2 instead of innerHTML.
   * In Mozilla, innerHTML= is like innerText= at standalone flash URLs.
   */
  var table = document.createElement("table");
  controlsDiv.appendChild(table);
  
  var row = table.insertRow(-1);
  
  var pauseButton = document.createElement("button");
  pauseButton.appendChild(document.createTextNode("Pause"));
  var buttonCell = row.insertCell(-1);
  buttonCell.appendChild(pauseButton);
  
  var slider = row.insertCell(-1);
  slider.width = "100%";
  
  var visibleSlider = document.createElement("div");
  visibleSlider.style.position = "relative";
  visibleSlider.style.height = "10px";
  visibleSlider.style.width = "100%";
  visibleSlider.style.MozBorderRadius = "4px";
  visibleSlider.style.background = "#aaa";
  slider.appendChild(visibleSlider);
  
  var thumb = document.createElement("div");
  thumb.style.position = "absolute";
  thumb.style.height = "20px";
  thumb.style.width = "10px";
  thumb.style.top = "-5px";
  thumb.style.MozBorderRadius = "4px";
  thumb.style.background = "#666";
  visibleSlider.appendChild(thumb);
  

  var sliderWidth;
  var paused = false;
  var dragging = false;

  table.width = Math.max(parseInt(flash.width) || 0, 400);
  
  addEvent(pauseButton, "click", pauseUnpause);
  addEvent(slider, "mousedown", drag);
  addEvent(slider, "drag", function() { return false; }); /* For IE */
  window.setInterval(update, 30);

  function pauseUnpause()
  {
    paused = !paused;

    pauseButton.style.borderStyle = paused ? "inset" : "";

    if (paused)
      flash.StopPlay();
    else
      flash.Play();
  }

  function update()
  {
    sliderWidth = parseInt(getWidth(slider) - getWidth(thumb));

    if (!paused && !dragging)
      thumb.style.left = parseInt(flash.CurrentFrame() / totalFrames() * sliderWidth) + "px";
  }

  function dragMousemove(e)
  {
    var pageX = e.clientX + document.body.scrollLeft; /* cross-browser, unlike e.pageX, which IE does not support */
    var pos = bounds(0, pageX - getX(slider) - 5, sliderWidth);
    var frame = bounds(1, Math.ceil(totalFrames() * pos / sliderWidth), totalFrames() - 2);

    thumb.style.left = pos + "px";

    flash.GotoFrame(frame);
  }

  function release(e)
  {
    removeEvent(document, "mousemove", dragMousemove);
    removeEvent(document, "mouseup", release);
    if (!paused)
      flash.Play();
    dragging = false;
  }

  function drag(e)
  {
    addEvent(document, "mousemove", dragMousemove);
    addEvent(document, "mouseup", release);
    dragging = true;
    dragMousemove(e);
  }



  /* Boring functions, some of which only exist to hide differences between IE and Mozilla. */

  function bounds(min, val, max)
  {
    return Math.min(Math.max(min, val), max);
  }

  function totalFrames()
  {
    /* This is weird.  TotalFrames differs between IE and Mozilla.  CurrentFrame does not. */

    if (typeof flash.TotalFrames == "number")
      return flash.TotalFrames; /* IE */
    else if (typeof flash.TotalFrames == "function")
      return flash.TotalFrames(); /* Mozilla */
    else
      return 1; /* Partially loaded Flash in IE? */
  }

  function getWidth(elem)
  {
    if (document.defaultView && document.defaultView.getComputedStyle)
      return parseFloat(document.defaultView.getComputedStyle(elem,null).getPropertyValue("width")); /* Mozilla */
    else
      return parseFloat(elem.offsetWidth); /* IE (currentStyle.width can be "auto" or "100%") */
  }

  function getX(elem)
  {
    if (!elem) return 0;
    return (elem.offsetLeft) + getX(elem.offsetParent);
  }

  function addEvent(elem, eventName, fun)
  {
    if (elem.addEventListener) /* Mozilla */
      elem.addEventListener(eventName, fun, false);
    else /* IE */
      elem.attachEvent("on" + eventName, fun);
  }

  function removeEvent(elem, eventName, fun)
  {
    if (elem.addEventListener)
      elem.removeEventListener(eventName, fun, false);
    else
      elem.detachEvent("on" + eventName, fun);
  }

}

}
</script>
</head>
<body onload="setupSeekBar();">
"""

# for emacs coloring: "


# normal header
NORMAL_HEADER = "</head><body>\n"


# generate_html
def generate_html(out, fname, seekbar=True, loop=True):
  parser = SWFParser()
  parser.open(fname, header_only=True)
  (x,width, y,height) = parser.rect
  basename = os.path.basename(fname)
  (title, ext) = os.path.splitext(basename)
  out.write('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN">\n'
           '<html>\n<head>\n<title>%s</title>' % title)
  if seekbar:
    out.write(SEEKBAR_HEADER)
  else:
    out.write(NORMAL_HEADER)
  dic = { 'title':title, 'width':int(width/20), 'height':int(height/20), 'basename':basename,
          'swf_version':parser.swf_version, 'loop':loop, 'pyvnc2swf_version': PYVNC2SWF_VERSION }
  out.write('<h1>%(title)s</h1>\n'
           '<hr noshade><center>\n'
           '<object classid="clsid:D27CDB6E-AE6D-11cf-96B8-444553540000" width="%(width)d" height="%(height)d"\n'
           ' codebase="http://download.macromedia.com/pub/shockwave/cabs/flash/swflash.cab#version=%(swf_version)d,0,0,0">\n'
           ' <param name="movie" value="%(basename)s">\n'
           ' <param name="play" value="true">\n'
           ' <param name="loop" value="%(loop)s">\n'
           ' <param name="quality" value="high">\n'
           '<embed src="%(basename)s" width="%(width)d" height="%(height)d" play="true"\n'
           ' loop="%(loop)s" quality="high" type="application/x-shockwave-flash"\n'
           ' pluginspage="http://www.macromedia.com/go/getflashplayer">\n'
           '</embed></object></center>\n'
           '<hr noshade>\n'
           '<div align=right>\n'
           '<em>Generated by <a href="http://www.unixuser.org/~euske/vnc2swf/">pyvnc2swf</a>-%(pyvnc2swf_version)s</em>\n'
           '</div></body></html>\n'
           % dic)
  return

# test
if __name__ == '__main__':
  import getopt
  def usage():
    print 'usage: %s [-S)eekbarless] [-L)oopless] file' % sys.argv[0]
    sys.exit(2)
  try:
    (opts, args) = getopt.getopt(sys.argv[1:], 'SL')
  except getopt.GetoptError:
    usage()
  (seekbar, loop) = (True, True)
  for (k, v) in opts:
    if k == '-S': seekbar = False
    elif k == '-L': loop = False
  if not args: usage()
  generate_html(sys.stdout, args[0], seekbar=seekbar, loop=loop)
