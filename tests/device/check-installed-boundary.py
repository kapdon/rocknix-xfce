#!/usr/bin/env python3
"""Read-only RP6 boundary audit; write-open probes never truncate or write.

Run as host root with Desktop active. Host-path access probes drop all groups
and become the mapped guest-root/user identities before opening any path.
This is a scoped permission/mount audit, not a kernel isolation proof.
"""
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys

base = Path('/storage/rocknix-desktop/managed/host')
assert os.getuid() == 0
assert subprocess.run(['systemctl', 'is-active', '--quiet',
                       'rocknix-desktop.service']).returncode == 0
paths = [base / name for name in (
    'bin/rocknix-lxc', 'bin/rocknix-lxc-desktop', 'bin/launch-sway-desktop',
    'bin/preflight', 'input/desktop.yaml',
    'host-tools/usr/lib/aarch64-linux-gnu/ld-linux-aarch64.so.1',
    'host-tools/usr/bin/lxc-start')]
paths += [Path('/storage/.config/system.d/rocknix-desktop.service'),
          Path('/usr/bin/FEX'), Path('/usr/bin/FEXServer')]
for path in paths:
    assert path.is_file(), path
    info = path.stat()
    assert info.st_uid == 0 and not info.st_mode & 0o022, path

probe = r'''
import errno,json,os,sys,stat
from pathlib import Path
for name in json.loads(sys.argv[1]):
    for parent in Path(name).parents:
        assert not os.access(parent,os.W_OK),'writable host ancestor: '+str(parent)
    try:
        fd=os.open(name,os.O_WRONLY|os.O_NONBLOCK)
    except OSError as error:
        assert error.errno in (errno.EACCES,errno.EPERM,errno.EROFS),(name,error)
    else:
        os.close(fd)
        raise RuntimeError('mapped identity can write host control file: '+name)
print('PASS: host control write-open denied for UID',os.getuid())
'''
for identity in (200000, 201000):
    def drop():
        os.setgroups([])
        os.setgid(identity)
        os.setuid(identity)
    subprocess.run([sys.executable, '-c', probe, json.dumps(list(map(str, paths)))],
                   preexec_fn=drop, check=True)

runtime = runpy.run_path(str(base / 'bin/rocknix-lxc'))['Runtime'](
    base / 'host-tools', Path('/storage/rocknix-desktop/data/rootfs'))
desktop = runpy.run_path(str(base / 'bin/rocknix-lxc-desktop'))
shares = []
for name in desktop['SHARED']:
    source = Path('/storage') / name
    if source.exists() or source.is_symlink():
        desktop['trusted_directory'](source, 0)
        shares.append(str(source))
guest = r'''
import errno,json,os,sys,stat
from pathlib import Path
assert os.getuid()==0
for name in ('uid_map','gid_map'):
    assert Path('/proc/self/'+name).read_text().split()==['0','200000','65536']
mounts={line.split()[4]:set(line.split()[5].split(','))
        for line in Path('/proc/self/mountinfo').read_text().splitlines()}
shares=set(json.loads(sys.argv[1]))
assert {name for name in mounts if name.startswith('/storage/')}==shares
assert '/storage' not in mounts
for name in ('/storage/scripts','/storage/rocknix-desktop','/dev/sda19',
             '/dev/uinput','/dev/hidraw0','/dev/dri/card0','/run/0-runtime-dir',
             '/run/docker.sock','/run/host','/run/systemd/private/host'):
    assert not os.path.lexists(name),name
assert '/dev/input' not in mounts  # Never bind the whole host input directory.
for node in Path('/dev/input').glob('*'):
    info=node.stat()
    assert stat.S_ISCHR(info.st_mode) and os.major(info.st_rdev)==13
    source=Path('/sys/class/input')/node.name/'device'
    assert str(source.resolve()).startswith('/sys/devices/virtual/misc/uhid/')
    assert (source/'name').read_text().strip()=='Sony Interactive Entertainment DualSense Wireless Controller'
    metadata='/run/udev/data/c13:'+str(os.minor(info.st_rdev))
    assert 'ro' in mounts[metadata]
    assert 'E:ID_INPUT_JOYSTICK=1' in Path(metadata).read_text()
for name in ('/run/rocknix-desktop','/run/rocknix-fex/ArchLinux',
             '/run/rocknix-fex/bin/FEX','/run/rocknix-fex/bin/FEXServer',
             '/run/rocknix-fex/lib/libfmt.so.12'):
    assert 'ro' in mounts[name],name
for name in ('/run/rocknix-fex/bin/FEX','/run/rocknix-fex/bin/FEXServer',
             '/run/rocknix-fex/lib/libfmt.so.12'):
    try:
        fd=os.open(name,os.O_WRONLY|os.O_NONBLOCK)
    except OSError as error:
        assert error.errno in (errno.EROFS,errno.EACCES,errno.EPERM),(name,error)
    else:
        os.close(fd)
        raise RuntimeError('guest root can write native runtime')
print(json.dumps({'guest_root_maps_to':200000,'shared_mounts':sorted(shares),
                  'host_runtime_write_open_denied':True,'broad_host_paths_absent':True}))
'''
result = runtime.attach('/usr/bin/python3', '-', json.dumps(shares), input=guest)
print(result.stdout, result.stderr, flush=True)
assert result.returncode == 0
# This object only attached to the existing Desktop: never close its runtime.
