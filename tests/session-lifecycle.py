#!/usr/bin/python3
"""Run the real session shell with isolated paths and long-lived mock clients."""
import os
from pathlib import Path
import shlex
import signal
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'rootfs-overlay/usr/local/bin/rocknix-sway-session').read_text()

for mode, expected in [('return', 0), ('invalid', 1), ('term', 143), ('waybar', 1), ('keyboard', 1), ('refresh', 0), ('xwayland', 1), ('x11-start', 1), ('workarea', 1)]:
    with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryFile() as log:
        home = Path(directory) / 'home'
        home.mkdir()
        runtime = Path(directory) / 'run'
        runtime.mkdir()
        fifo = Path(directory) / 'control'
        os.mkfifo(fifo)
        keyboard_fifo = Path(directory) / 'keyboard-control'
        os.mkfifo(keyboard_fifo)
        # Override only machine-specific paths; execute production lifecycle code.
        script = SOURCE.replace('export HOME=/home/rocknix',
                                f'export HOME={shlex.quote(str(home))}')
        script = script.replace('CONTROL_FIFO=/run/rocknix-desktop/control',
                                f'CONTROL_FIFO={shlex.quote(str(fifo))}')
        script = script.replace('RUNTIME_DIR=${XDG_RUNTIME_DIR:?}',
                                f'RUNTIME_DIR={shlex.quote(str(runtime))}')
        script = script.replace('/run/rocknix-desktop/keyboard-control', str(keyboard_fifo))
        metrics = Path(directory) / 'metrics.json'
        script = script.replace('/run/rocknix-desktop/display-metrics.json', str(metrics))
        visible = Path(directory) / 'keyboard-visible'
        script = script.replace('/run/rocknix-desktop/keyboard-visible', str(visible))
        script = script.replace('/etc/xdg/waybar/config.jsonc',
                                shlex.quote(str(ROOT / 'rootfs-overlay/etc/xdg/waybar/config.jsonc')))
        script = script.replace('/etc/xdg/waybar/style.css',
                                shlex.quote(str(ROOT / 'rootfs-overlay/etc/xdg/waybar/style.css')))
        script = script.replace('source /usr/local/bin/rocknix-home-integration',
                                'refresh_storage_links() { :; }')
        script = script.replace('refresh_home_integration /home/rocknix-default "$HOME"', ':')
        script = script.replace('/opt/rocknix-xwayland/bin/xwayland-satellite', 'satellite')
        script = script.replace('timeout .2 xdpyinfo', 'xdpyinfo')
        script = script.replace('/usr/local/bin/rocknix-x11-workarea', 'workarea')
        satellite = 'sleep 0.2; return 1' if mode in ('xwayland', 'x11-start') else 'exec sleep 600'
        ready = 'return 1' if mode == 'x11-start' else 'return 0'
        bar = 'sleep 0.2; return 1' if mode == 'waybar' else 'exec sleep 600'
        keyboard = 'sleep 0.2; return 1' if mode == 'keyboard' else 'exec sleep 600'
        starts = Path(directory) / 'starts'
        area = 'sleep 0.2; return 1' if mode == 'workarea' else 'exec sleep 600'
        mocks = (f'workarea() {{ {area}; }}\n'
                 f'satellite() {{ echo x11 >>{shlex.quote(str(starts))}; {satellite}; }}\n'
                 f'xdpyinfo() {{ {ready}; }}\n'
                 f'waybar() {{ echo bar >>{shlex.quote(str(starts))}; {bar}; }}\n'
                 f'thunar() {{ echo app >>{shlex.quote(str(starts))}; exec sleep 600; }}\n'
                 f'wvkbd-rocknix() {{ echo "keyboard $*" >>{shlex.quote(str(starts))}; {keyboard}; }}\n')
        proc = subprocess.Popen(['bash', '-c', mocks + script],
                                env={**os.environ, 'ROCKNIX_KEYBOARD_HEIGHT': '378',
                                     'ROCKNIX_KEYBOARD_FONT_SIZE': '30', 'ROCKNIX_OUTPUT_NAME': 'test'},
                                stdout=log, stderr=log, start_new_session=True)
        try:
            if mode == 'refresh':
                deadline = time.monotonic() + 3
                while not starts.exists() or 'app' not in starts.read_text():
                    assert time.monotonic() < deadline
                    time.sleep(.02)
                visible.touch()
                metrics.write_text('{"generation":1}\n')
                while starts.read_text().count('bar') < 2:
                    assert proc.poll() is None, 'refresh killed Desktop session'
                    assert time.monotonic() < deadline, 'UI refresh did not finish'
                    time.sleep(.02)
                assert starts.read_text().count('x11') == 1, 'refresh restarted Xwayland'
                assert starts.read_text().count('app') == 1, 'refresh relaunched user apps'
                keyboards = [line for line in starts.read_text().splitlines() if line.startswith('keyboard ')]
                assert len(keyboards) == 2 and '--hidden' in keyboards[0] and '--hidden' not in keyboards[1]
            if mode in ('return', 'invalid', 'refresh'):
                deadline = time.monotonic() + 3
                while True:
                    try:
                        fd = os.open(fifo, os.O_WRONLY | os.O_NONBLOCK)
                        break
                    except OSError:
                        if time.monotonic() >= deadline:
                            raise AssertionError('session did not read FIFO')
                        time.sleep(0.02)
                os.write(fd, b'invalid\n' if mode == 'invalid' else b'return\n')
                os.close(fd)
            elif mode == 'term':
                time.sleep(0.2)
                proc.send_signal(signal.SIGTERM)
            assert proc.wait(timeout=3) == expected, mode
        finally:
            # Model systemd cgroup cleanup, including deliberately lingering apps.
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait()
        print(f'PASS: session {mode} exits without waiting for application children')
