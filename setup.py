from setuptools import setup, find_packages
import sys, os

version = '1.0'

setup(name='castro',
      version=version,
      description="Screencasting library",
      long_description="""\

------------
Introduction
------------

Castro is a library for recording automated screencasts via a simple API.

Here's an example::

    >>> from castro import Castro
    >>> c = Castro()
    >>> c.start() >>> # Do something awesome!
    >>> c.stop()

-------
Install
-------

::

    1) Install and launch a vncserver. (Hint: Google it.)
    2) $ [sudo] easy_install castro
    3) There's no step 3!

----
Test
----

::

    $ python -c "import castro; castro.test()"

-----
Watch
-----

Video stored in: <default_temp_dir>/castro-video.swf

Video player stored in: <default_temp_dir>/castro-video.html

Linux/OSX::

    $ firefox /tmp/castro-video.html




--------------------
License & Repository
--------------------

Castro was created by `Jason Huggins <http://jrandolph.com>`_. It is licensed under
the GPLv2, since it is a derivative work of pyvnc2swf, which is also
licensed under the GPLv2. 

Castro has a `git respository at github.com <http://github.com/hugs/castro>`_.


-------
Summary
-------

Castro is a minor fork of pyvnc2swf, allowing one to use pyvnc2swf as a 
regular Python library, instead of a Tk GUI application or command line 
utility. 

The specific improvement Castro brings to pyvnc2swf is the ability to start 
and stop recording programmatically via a simple Python API. Castro 
uses a file-based IPC to tell pyvnc2swf when to stop recording.

Ordinarily, pyvnc2swf's command line utility, vnc2swf.py, expects users to 
stop recording by manually typing "Control-C", sending a KeyboardInterrupt 
and allowing the process to exit cleanly. On Linux, emulating KeyboardInterrupt
is simple enough to do by sending a SIGINT signal. But this does not work cross-
platform, specifically on Windows. And a big reason for using pyvnc2swf is its
ability to record vnc video on any platform *from* any platform.

------------
Dependencies
------------

* Python - 2.5 or above

* Pygame - 1.6 or above

* Processing - 0.52 or above

* Simplejson - 2.0.9 or above

""",
      # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
          'Development Status :: 4 - Beta',
          'Environment :: MacOS X',
          'Environment :: Win32 (MS Windows)',
          'Environment :: X11 Applications',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: GNU General Public License (GPL)',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Topic :: Multimedia :: Graphics :: Capture :: Screen Capture',
          'Topic :: Software Development :: Libraries :: Python Modules',
      ],
      keywords='pyvnc2swf screencast video',
      author='Jason R. Huggins',
      author_email='jason@jrandolph.com',
      url='http://github.com/hugs/castro',
      license='GPL',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          # -*- Extra requirements: -*-
          'processing',
          'pygame',
          'setuptools',
          'simplejson',
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
