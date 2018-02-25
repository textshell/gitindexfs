gitindexfs
=======

gitindexfs is a `FUSE <http://fuse.sourceforge.net/>`_-filesystem that mounts 
the index of a git repositories read only, allowing direct access to the staged 
state of a git checkout through the filesystem.


Installation
------------

Use an python3 virtual env::

  $ python3 -mvenv venv
  $ ./venv/bin/pip install .


Example usage
-------------

Try this in an git checkout:

Create a mountpoint and mount the current directory:

  $ mkdir _index
  $ gitindexfs _index
  $ ls _index

Unmount with 

  $ fusermount -u _index

Thanks
------

This program was initially based on legitfs by Marc Brinkmann (see https://github.com/mbr/legitfs/ )
