"""Read-only cgroup-v2 evidence for a cooperating host Steam broker POC.

Paths are trusted supervisor inputs, never values from a guest or Steam VDF.
No cgroups/processes are created, stopped, moved or removed here.
"""
import os
from pathlib import Path
import stat


class Unknown(RuntimeError):
    pass


def populated(text):
    fields = {}
    for line in text.splitlines():
        pair = line.split()
        if len(pair) != 2 or pair[0] in fields:
            raise Unknown('malformed cgroup.events')
        fields[pair[0]] = pair[1]
    if fields.get('populated') not in ('0', '1'):
        raise Unknown('missing or invalid populated state')
    return fields['populated'] == '1'


class ScopeSet:
    """Require both tracked scopes to exist and remain empty during observation.

A missing scope is UNKNOWN, not proof that Steam stopped. The future broker
must retain empty scopes until cleanup/recovery completes or obtain separate
trusted systemd/process evidence for a scope that systemd already collected.
The cgroup2 root and names must come from verified host configuration. This
reader does not verify mount type or intercept uncooperative native launches.
"""
    def __init__(self, root, names, owner=0):
        self.root = Path(root)
        self.names = tuple(names)
        self.owner = owner
        if len(self.names) != 2 or len(set(self.names)) != 2:
            raise ValueError('two distinct native/container scopes required')
        for name in self.names:
            if not name or name.startswith('/') or any(
                    part in ('', '.', '..') for part in name.split('/')):
                raise ValueError('unsafe relative scope path')

    def _open_dir(self, path, parent_fd=None):
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                     dir_fd=parent_fd)
        info = os.fstat(fd)
        if info.st_uid != self.owner or info.st_mode & 0o022:
            os.close(fd)
            raise Unknown('scope path must be host controlled')
        return fd

    def _sample(self, root_fd, name):
        current = os.dup(root_fd)
        try:
            for part in name.split('/'):
                child = self._open_dir(part, current)
                os.close(current)
                current = child
            info = os.fstat(current)
            fd = os.open('cgroup.events', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                         dir_fd=current)
            with os.fdopen(fd) as stream:
                entry = os.fstat(stream.fileno())
                if not stat.S_ISREG(entry.st_mode) or entry.st_uid != self.owner or entry.st_mode & 0o022:
                    raise Unknown('untrusted cgroup.events')
                text = stream.read(4097)
                if len(text) > 4096:
                    raise Unknown('oversized cgroup.events')
            return (info.st_dev, info.st_ino), populated(text)
        finally:
            os.close(current)

    def empty(self):
        # A double sample can detect replacement between reads, not make an
        # atomic kernel snapshot. The broker lock must already be held, every
        # supported launcher must cooperate, and guest migration out of the
        # tracked ancestor must be prevented by the host cgroup boundary.
        try:
            root_fd = self._open_dir(self.root)
            try:
                first = [self._sample(root_fd, name) for name in self.names]
                second = [self._sample(root_fd, name) for name in self.names]
            finally:
                os.close(root_fd)
        except (OSError, UnicodeError) as error:
            raise Unknown(f'cannot establish Steam scope state: {error}') from error
        if [x[0] for x in first] != [x[0] for x in second]:
            raise Unknown('scope replaced during observation')
        return not any(state for _, state in first + second)
