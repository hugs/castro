# Makefile (only for maintainance purpose)
# $Id: Makefile,v 1.1 2008/11/15 10:07:09 euske Exp $
#
#  Copyright (C) 2005 by Yusuke Shinyama (yusuke at cs . nyu . edu)
#  All Rights Reserved.
#
#  This is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This software is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this software; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307,
#  USA.
#

all:

clean:
	-rm *.pyc *~ '.#*' .DS_Store 

test:
	x11vnc -quiet -localhost -viewonly -nopw -bg
	./vnc2swf.py -n -o out.swf localhost:0
