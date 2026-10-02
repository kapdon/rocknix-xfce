#!/usr/bin/python3
"""Constrain the signed-APT Xwayland dependency payload to guest X11 packages."""
from pathlib import Path
import subprocess
import sys

ALLOWED = {'xwayland', 'x11-xkb-utils', 'x11-utils', 'xserver-common',
           'libfontenc1', 'libxaw7', 'libxcvt0', 'libxfont2', 'libxkbfile1',
           'libxxf86dga1'}
REQUIRED = {'xwayland', 'x11-xkb-utils', 'x11-utils'}


def packages(directory):
    result = {}
    for path in sorted(directory.glob('*.deb')):
        if path.is_symlink() or not path.is_file():
            raise RuntimeError('package must be a regular file')
        fields = [subprocess.check_output(['dpkg-deb', '-f', str(path), key], text=True).strip()
                  for key in ('Package', 'Version', 'Architecture')]
        name, version, arch = fields
        if name not in ALLOWED or arch not in ('arm64', 'all') or name in result:
            raise RuntimeError('unexpected or duplicate X11 dependency: ' + name)
        result[name] = (path, version)
    if not REQUIRED <= result.keys():
        raise RuntimeError('required X11 packages are missing')
    return result


if __name__ == '__main__':
    packages(Path(sys.argv[1]))
