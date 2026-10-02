#!/usr/bin/python3
"""Exercise offline X11 maintenance selection and fail-closed APT planning."""
from pathlib import Path
import runpy
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
api = runpy.run_path(str(ROOT / 'build-support/xwayland/install-image.py'))
main = api['main']
candidates = {'xwayland': (Path('/fixture/xwayland.deb'), '2'),
              'x11-utils': (Path('/fixture/x11-utils.deb'), '2')}


def exercise(plan, current='1'):
    calls = []
    def run(argv, **kwargs):
        calls.append(argv)
        if argv[0] == 'dpkg-query':
            return subprocess.CompletedProcess(argv, 0, 'installed ' + current)
        if argv[0] == 'dpkg':
            return subprocess.CompletedProcess(argv, 0 if current == '3' else 1)
        return subprocess.CompletedProcess(argv, 0)
    def output(argv, **kwargs):
        if argv[0] == 'apt-mark':
            return 'x11-utils\n'
        if '--simulate' in argv:
            return plan
        return ''
    with patch.object(sys, 'argv', ['install-image.py', '/fixture', '--retained']), \
         patch('runpy.run_path', return_value={'packages': lambda _: candidates}), \
         patch('subprocess.run', side_effect=run), \
         patch('subprocess.check_output', side_effect=output):
        main()
    return calls

calls = exercise('Inst xwayland\nConf xwayland\nInst x11-utils\nConf x11-utils\n')
assert any(call[:2] == ['apt-get', '-y'] for call in calls)
assert ['apt-mark', 'auto', 'x11-utils'] in calls
assert not any(call[0] == 'apt-get' for call in exercise('', current='3'))
for plan in ('Remv firefox-esr\n', 'Purg xwayland\n', 'Inst libc6\n', 'Conf libc6\n'):
    try:
        exercise(plan)
    except RuntimeError:
        pass
    else:
        raise AssertionError('unsafe package plan accepted: ' + plan)
print('PASS: offline X11 updates preserve newer packages and reject unrelated mutations')
