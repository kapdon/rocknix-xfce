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
        self.fd = None

    def acquire(self):
        # Caller creates a private, trusted directory; production must additionally
        # validate host-root ownership and every ancestor. Never guest-writable.
        info = self.directory.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_mode & 0o077:
            raise ValueError('lease directory must be private')
        if self.side not in ('native', 'lxc'):
            raise ValueError('unknown side')
        self.fd = os.open(self.directory / 'lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            marker = self.directory / 'active'
            if os.path.lexists(marker) or not self.scopes_empty():
                raise Busy('Close Steam in the other environment first; recovery may be required.')
            with marker.open('x') as stream:
                stream.write(self.side + '\n')
                stream.flush()
                os.fsync(stream.fileno())
        except BaseException:
            self.close_fd()
            raise
        return self

    def release(self):
        if self.fd is None:
            raise RuntimeError('lease not held')
        if not self.scopes_empty():
            raise Busy('Steam children still active; retain lease and mounts')
        (self.directory / 'active').unlink()
        self.close_fd()

    def close_fd(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    @staticmethod
    def recover(directory, scopes_empty):
        # Explicit recovery: a dead PID alone is never sufficient. Real adapters
        # must query both host-owned cgroups and refuse on failed/unknown queries.
        lease = Lease(directory, 'native', scopes_empty)
        lease.fd = os.open(Path(directory) / 'lock', os.O_RDWR | os.O_NOFOLLOW)
        try:
            fcntl.flock(lease.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if not scopes_empty():
                raise Busy('recovery refused while either scope is populated')
            (Path(directory) / 'active').unlink(missing_ok=True)
        finally:
            lease.close_fd()
