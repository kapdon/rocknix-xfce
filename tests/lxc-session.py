#!/usr/bin/python3
"""Exercise session endpoint setup without starting a desktop or changing IDs."""
import os
from pathlib import Path
import socket
import subprocess
import tempfile

source = Path('rootfs-overlay/usr/local/bin/rocknix-lxc-session').read_text()
with tempfile.TemporaryDirectory(prefix='rocknix-session-test-') as directory:
    root = Path(directory)
    runtime = root / 'runtime'
    runtime.mkdir(mode=0o700)
    bridge = root / 'bridge'
    bridge.mkdir()
    fifo = bridge / 'control'
    os.mkfifo(fifo)
    endpoint = bridge / 'wayland-1'
    listener = socket.socket(socket.AF_UNIX)
    listener.bind(str(endpoint))
    mock = root / 'bin'
    mock.mkdir()
    identity = mock / 'id'
    identity.write_text('#!/bin/sh\ncase "$1" in -u) echo 1000;; -un) echo rocknix;; *) exit 1;; esac\n')
    identity.chmod(0o755)
    client = mock / 'session-client'
    client.write_text('#!/bin/sh\nset -e\ntest "$WAYLAND_DISPLAY" = wayland-1\n'
                      'test -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY"\n'
                      'test "$XDG_CURRENT_DESKTOP" = ROCKNIX\ntest "$GDK_BACKEND" = wayland\n')
    client.chmod(0o755)
    script = root / 'session'
    script.write_text(source.replace('/run/rocknix-desktop/control', str(fifo)).replace(
        '/usr/bin/dbus-run-session -- /usr/local/bin/rocknix-sway-session', str(client)))
    env = dict(os.environ, PATH=str(mock) + ':' + os.environ['PATH'],
               WAYLAND_DISPLAY=str(endpoint), XDG_RUNTIME_DIR=str(runtime),
               XDG_CURRENT_DESKTOP='gamescope', GDK_BACKEND='x11')
    for _ in range(2):
        subprocess.run(['bash', str(script)], env=env, check=True)
        assert (runtime / 'wayland-1').is_symlink()
        assert (runtime / 'wayland-1').resolve() == endpoint
    fifo.unlink()
    result = subprocess.run(['bash', str(script)], env=env, capture_output=True, text=True)
    assert result.returncode != 0 and 'control endpoint missing' in result.stderr
    os.mkfifo(fifo)
    endpoint.unlink()
    result = subprocess.run(['bash', str(script)], env=env, capture_output=True, text=True)
    assert result.returncode != 0 and 'Wayland endpoint missing' in result.stderr
    listener.close()
print('PASS: session exports a lock-safe display basename and rejects missing endpoints')
