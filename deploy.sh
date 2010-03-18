#! /bin/sh
# TODO: Find a way to preserve old versions on PyPI when pushing new versions
 
rm -rf build castro.egg-info dist
python setup.py bdist_egg upload
python setup.py sdist upload
python setup.py register
