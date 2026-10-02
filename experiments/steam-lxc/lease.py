"""Cooperating-supervisor POC, not a device process detector or Steam launcher."""
import fcntl
import os
from pathlib import Path
import stat


class Busy(RuntimeError):
    pass


class Lease:
    def __init__(self, directory, side, scopes_empty):
        self.directory = Path(directory)
        self.side = side
        self.scopes_empty = scopes_empty
        self.fd = self.dirfd = None

    def _directory(self):
        # Descriptor traversal rejects symlink ancestors. Root-owned sticky /tmp
        # supports disposable fixtures; production state belongs under /run or
        # managed/host/state. Only the terminal directory may contain lease data.
        if not self.directory.is_absolute() or '..' in self.directory.parts:
            raise ValueError('absolute canonical lease directory required')
        fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
        try:
            for part in self.directory.parts[1:]:
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = child
                info = os.fstat(fd)
                sticky_root = info.st_uid == 0 and info.st_mode & stat.S_ISVTX
                if info.st_uid not in (0, os.geteuid()) or (info.st_mode & 0o022 and not sticky_root):
                    raise ValueError('untrusted lease ancestor')
            info = os.fstat(fd)
            if info.st_uid != os.geteuid() or info.st_mode & 0o077:
                raise ValueError('lease directory must be private and owned by supervisor')
            return fd
        except BaseException:
            os.close(fd)
            raise

    @staticmethod
    def _file(fd):
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or \
                info.st_mode & 0o077 or info.st_nlink != 1:
            raise ValueError('lease file must be private, singly linked and supervisor-owned')

    def _lock(self, create):
        if self.fd is not None or self.dirfd is not None:
            raise RuntimeError('lease already held')
        self.dirfd = self._directory()
        try:
            flags = os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK
            self.fd = os.open('lock', flags | (os.O_CREAT if create else 0), 0o600, dir_fd=self.dirfd)
            self._file(self.fd)
            try:
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise Busy('Close Steam in the other environment first.') from error
        except BaseException:
            self.close_fd()
            raise

    def _marker_exists(self):
        try:
            os.stat('active', dir_fd=self.dirfd, follow_symlinks=False)
            return True
        except FileNotFoundError:
            return False

    def acquire(self):
        if self.side not in ('native', 'lxc'):
            raise ValueError('unknown side')
        self._lock(create=True)
        try:
            if self._marker_exists() or not self.scopes_empty():
                raise Busy('Close Steam in the other environment first; recovery may be required.')
            fd = os.open('active', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=self.dirfd)
            with os.fdopen(fd, 'w') as stream:
                stream.write(self.side + '\n')
                stream.flush()
                os.fsync(stream.fileno())
            os.fsync(self.dirfd)
        except BaseException:
            self.close_fd()
            raise
        return self

    def _clear_marker(self):
        if not self._marker_exists():
            return
        fd = os.open('active', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=self.dirfd)
        try:
            self._file(fd)
        finally:
            os.close(fd)
        os.unlink('active', dir_fd=self.dirfd)
        os.fsync(self.dirfd)

    def release(self):
        if self.fd is None:
            raise RuntimeError('lease not held')
        if not self.scopes_empty():
            raise Busy('Steam children still active; retain lease and mounts')
        self._clear_marker()
        self.close_fd()

    def close_fd(self):
        for attribute in ('fd', 'dirfd'):
            fd = getattr(self, attribute)
            if fd is not None:
                os.close(fd)
                setattr(self, attribute, None)

    @staticmethod
    def recover(directory, scopes_empty):
        # A dead PID alone is never sufficient. Failed/unknown evidence raises
        # without clearing the active marker. Keep the lock inode permanently.
        lease = Lease(directory, 'native', scopes_empty)
        lease._lock(create=False)
        try:
            if not scopes_empty():
                raise Busy('recovery refused while either scope is populated')
            lease._clear_marker()
        finally:
            lease.close_fd()
