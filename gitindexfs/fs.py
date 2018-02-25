from collections import Counter
from itertools import count
from errno import ENOENT, EROFS
import os
from stat import S_IFDIR
from threading import RLock

from fuse import FuseOSError, Operations, LoggingMixIn
from logbook import Logger

log = Logger('fs')


class DescriptorManager(object):
    def __init__(self):
        self.refcount = Counter()
        self.data_hash = {}
        self.lock = RLock()
        self.fd = count()

    def get_free_fd(self, h):
        fd = next(self.fd)
        self.data_hash[fd] = h
        return fd

    def get_hash(self, fd):
        return self.data_hash[fd]

    def release(self, fd):
        with self.lock:
            newval = max(self.refcount[fd] - 1, 0)
            self.refcount[fd] = newval
            if newval == 0:
                del self.data_hash[fd]

            return newval != 0


class BlobNode:
    
    def __init__(self, fs, obj, mode):
        self.fs = fs
        self.obj = obj
        self.mode = mode
    
    def getattr(self):
        st = self.fs.empty_stat.copy()
        st['st_mode'] = self.mode
        st['st_size'] = self.obj.raw_length()
        return st

    def open(self, flags):
        with self.fs.data_lock:
            fd = self.fs.fd_man.get_free_fd(self.obj.id)

            # load data into data_cache
            if self.obj.id not in self.fs.data_cache:
                self.fs.data_cache[self.obj.id] = self.obj.as_raw_string()

            return fd

    def read(self, size, offset, fh):
        # lookup hash associated with filehandle
        h = self.fs.fd_man.get_hash(fh)

        # retrieve cached data for filehandle
        data = self.fs.data_cache[h]

        return data[offset:offset + size]

    def release(self, fh):
        with self.fs.data_lock:
            h = self.fs.fd_man.get_hash(fh)

            del self.fs.data_cache[h]

        return 0


class DirNode:
    def __init__(self, fs):
        self.fs = fs
        self.dirs = []
        self.files = []

    def getattr(self):
        st = self.fs.empty_stat.copy()
        st['st_mode'] |= S_IFDIR
        return st
    
    def readdir(self):
        entries = ['.', '..']

        entries += self.dirs
        entries += self.files

        return entries


class IndexFS(LoggingMixIn, Operations):
    def __init__(self, root, repo, mountpoint):
        self.root = os.path.abspath(root)
        self.mountpoint = os.path.abspath(mountpoint)

        root_stat = os.lstat(root)

        self.empty_stat = {
            'st_atime': 0,
            'st_ctime': 0,
            'st_gid': root_stat.st_gid,
            'st_mode': 0o644,
            'st_mtime': 0,
            'st_nlink': 1,
            'st_size': 0,
            'st_uid': root_stat.st_uid,
        }

        self.data_cache = {}
        self.data_lock = RLock()
        self.fd_man = DescriptorManager()
        self.passthrough_man = DescriptorManager()

        self.repo = repo
        self.dirs = {}

        index = self.repo.open_index()

        self.dirs['/'] = DirNode(self)

        self.files = {}

        for (fpath, bid, mode) in index.iterblobs():
            components = fpath.decode().split('/')

            d = self.dirs['/']
            p = ''
            for c in components[:-1]:
                p += '/' + c
                if p not in self.dirs:
                    self.dirs[p] = DirNode(self)
                    d.dirs.append(c)
                d = self.dirs[p]

            d.files.append(components[-1])
            p = p + '/' + components[-1]
            self.files[p] = BlobNode(self, self.repo.get_object(bid), mode)

    def _get_path(self, path):
        orig_path = path

        rv = split_git(os.path.join(self.root, path))

        # for debugging
        log.debug(log.debug('{} => {}'.format(orig_path, rv)))
        return rv

    def _get_node(self, path):
        if not path.startswith('/'):
            path = '/' + path

        if path not in self.dirs and path not in self.files:
            log.debug(log.debug('{} => ENOENT'.format(path)))
            raise FuseOSError(ENOENT)

        if path in self.dirs:
            rv = self.dirs[path]
        else:
            rv = self.files[path]
        log.debug(log.debug('{} => {}'.format(path, rv)))
        return rv

    def readdir(self, path, fh=None):
        node = self._get_node(path)
        return node.readdir()

    def getattr(self, path, fh=None):
        node = self._get_node(path)
        return node.getattr()

    def open(self, path, flags=0):
        if flags & (os.O_WRONLY | os.O_RDWR):
            raise FuseOSError(EROFS)

        node = self._get_node(path)
        return node.open(flags)

    def read(self, path, size, offset, fh):
        node = self._get_node(path)
        return node.read(size, offset, fh)

    def release(self, path, fh):
        # note: for some reason, this isn't called?
        # flush is though...
        node = self._get_node(path)
        return node.release(fh)

    def readlink(self, path):
        node = self._get_node(path)
        return node.readlink()
