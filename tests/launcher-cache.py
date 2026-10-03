#!/usr/bin/env python3
"""Settings and confirmation must never overwrite application usage ordering."""
import os
from pathlib import Path
import subprocess
import tempfile
from decimal import Decimal

launcher = Path('rootfs-overlay/usr/local/bin/rocknix-launcher').resolve()
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    (root / 'rocknix-launcher-pin').symlink_to(launcher.with_name('rocknix-launcher-pin'))
    stub = root / 'rocknix-fuzzel'
    stub.write_text('#!/bin/sh\nprintf "%s\\n" "$@" >"$ARGS"\n'
                    'case " $* " in *" --dmenu "*) cat >"$MENU";; esac\n')
    stub.chmod(0o755)
    env = {**os.environ, 'HOME': directory, 'XDG_CACHE_HOME': str(root / 'cache'),
           'PATH': directory + ':' + os.environ['PATH'], 'ARGS': str(root / 'args'),
           'MENU': str(root / 'menu')}
    for mode in ('apps', 'gamescope-apps', 'settings', 'confirm-return'):
        subprocess.run(['bash', str(launcher), mode], env=env, check=True)
        args = (root / 'args').read_text().splitlines()
        caches = [arg for arg in args if arg.startswith('--cache=')]
        expected = root / 'cache' / ('rocknix-fuzzel-gamescope' if mode == 'gamescope-apps' else 'rocknix-fuzzel') if mode in ('apps', 'gamescope-apps') else '/dev/null'
        assert caches == [f'--cache={expected}'], (mode, caches)
        if mode == 'gamescope-apps':
            assert '--launch-prefix=/usr/local/bin/rocknix-gamescope-app' in args
            assert '--prompt=GAMESCOPE  ' in args
        else:
            assert not any(arg.startswith('--launch-prefix=') for arg in args)
        if mode == 'confirm-return':
            assert '--no-sort' in args
            assert '--prompt=EXIT?  ' in args
            assert (root / 'menu').read_text().splitlines() == [
                'Cancel — stay in Desktop Mode',
                'Exit Desktop — close desktop apps',
            ]
    # Physical RP6 and narrow logical outputs, with keyboard space reserved.
    # Fuzzel's points scale with the output; explicit px do not. Keep row
    # geometry in logical pixels, then verify the physical rendering equation.
    for width, height, bar, keyboard, row, pad, scale in (
        (1920, 1080, 80, 378, 88, 19, '1'),
        (1280, 720, 54, 252, 59, 13, '1.5'),
        (960, 540, 44, 189, 44, 10, '2'),
        (800, 480, 40, 168, 38, 10, '1'),
    ):
        sizing = dict(env, ROCKNIX_LOGICAL_WIDTH=str(width),
                      ROCKNIX_LOGICAL_HEIGHT=str(height), ROCKNIX_BAR_HEIGHT=str(bar),
                      ROCKNIX_KEYBOARD_HEIGHT=str(keyboard), ROCKNIX_LAUNCHER_FONT_SIZE='20',
                      ROCKNIX_OUTPUT_SCALE=scale,
                      ROCKNIX_LAUNCHER_LINE_HEIGHT=str(row),
                      ROCKNIX_LAUNCHER_HORIZONTAL_PAD='12',
                      ROCKNIX_LAUNCHER_VERTICAL_PAD=str(pad))
        for mode in ('apps', 'gamescope-apps', 'settings', 'confirm-return'):
            subprocess.run(['bash', str(launcher), mode], env=sizing, check=True)
            args = (root / 'args').read_text().splitlines()
            points = Decimal(next(a.split('=')[1] for a in args if a.startswith('--line-height=')))
            assert points * Decimal(96) / Decimal(72) == row
            assert points * Decimal(96) / Decimal(72) * Decimal(scale) == row * Decimal(scale)
            lines = int(next(a.split('=')[1] for a in args if a.startswith('--lines=')))
            assert lines >= 1
            assert (lines + 1) * row + 2 * pad + 6 <= height - bar - keyboard - 48
print('PASS: only app launches use the favorites/usage cache')
print('PASS: launcher rows and chrome fit keyboard-visible RP6 and narrow output budgets')
