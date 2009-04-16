# Makefile (only for maintainance purpose)
# $Id: Makefile,v 1.29 2008/11/16 02:54:22 euske Exp $
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

CVSROOT=:ext:euske@vnc2swf.cvs.sourceforge.net:/cvsroot/vnc2swf
PACKAGE=pyvnc2swf
VERSION=0.9.5

PYTHON=python
GNUTAR=tar
ZIP=zip
CVS=cvs -d$(CVSROOT)

WORKDIR=/tmp
DISTNAME=$(PACKAGE)-$(VERSION)

all:

clean:
	-rm *~ '.#*' .DS_Store
	-cd bin && rm *~ '.#*' .DS_Store 
	-cd docs && rm *~ '.#*' .DS_Store 
	cd pyvnc2swf && make clean

up: clean
	$(CVS) update
diff: clean
	$(CVS) diff -u
commit: clean
	$(CVS) commit

check:
	cd pyvnc2swf && pychecker vnc2swf.py

pack: clean
	cd $(WORKDIR) && $(CVS) export -D now -d $(DISTNAME) pyvnc2swf
	cd $(WORKDIR) && $(GNUTAR) c -z -f $(WORKDIR)/$(DISTNAME).tar.gz $(DISTNAME) --dereference --numeric-owner
	cd $(WORKDIR) && $(ZIP) -r $(DISTNAME).zip $(DISTNAME)
	cd $(WORKDIR) && rm -rf $(DISTNAME)

WEBDIR=$(HOME)/Site/unixuser.org/vnc2swf/
publish: pack
	mv $(WORKDIR)/$(DISTNAME).tar.gz $(WEBDIR)
	mv $(WORKDIR)/$(DISTNAME).zip $(WEBDIR)
	cp docs/*.html $(WEBDIR)
