#!/usr/bin/python3
"""Pin ordering and desktop-entry argv survive the generic Gamescope path."""
from pathlib import Path
import os
import runpy
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

pin_api = runpy.run_path('rootfs-overlay/usr/local/bin/rocknix-launcher-pin')
app = runpy.run_path('rootfs-overlay/usr/local/bin/rocknix-gamescope-app')
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    cache = root / 'apps'
    cache.write_text('app.desktop|82\nother.desktop|7\nrocknix-gamescope.desktop|1\n')
    for _ in range(3):
        pin_api['pin'](cache)
        counts = dict(line.rsplit('|', 1) for line in cache.read_text().splitlines())
        assert counts == {'app.desktop':'82', 'other.desktop':'7', 'rocknix-gamescope.desktop':'83'}
    cache.write_text('app.desktop|2147483646\nother.desktop|2\n')
    pin_api['pin'](cache)
    counts = {name:int(value) for name,value in (line.rsplit('|',1) for line in cache.read_text().splitlines())}
    assert counts['rocknix-gamescope.desktop'] > counts['app.desktop'] > counts['other.desktop']
    assert max(counts.values()) < 2147483647
    with patch.dict(os.environ, XDG_STATE_HOME=directory, DESKTOP_ENTRY_ID='example.desktop'), \
            patch('subprocess.run', return_value=SimpleNamespace(returncode=0)) as run:
        command = ['wine', '/games/a game.exe', '$(touch /tmp/not-a-command)', '--flag']
        app['main'](command)
        argv = run.call_args.args[0]
        assert argv[:4] == ['/usr/local/bin/rocknix-gamescope', '--', '/usr/local/bin/rocknix-gamescope-app', '--child']
        assert argv[5:] == command
        assert run.call_args.kwargs.get('shell', False) is False
        assert (root / 'rocknix-desktop/gamescope-app.log').exists()
    with patch.dict(os.environ, XDG_STATE_HOME=directory, DESKTOP_ENTRY_ID='example.desktop'), \
            patch('subprocess.run', return_value=SimpleNamespace(returncode=1)), \
            patch.dict(app['main'].__globals__, message=lambda text: notices.append(text)):
        notices = []
        app['main'](['wine', 'game.exe'])
        assert len(notices) == 1 and 'failed' in notices[0]
    def compositor_teardown(argv, **kwargs):
        Path(argv[4]).write_text('0')
        return SimpleNamespace(returncode=-6)
    with patch.dict(os.environ, XDG_STATE_HOME=directory, DESKTOP_ENTRY_ID='example.desktop'), \
            patch('subprocess.run', side_effect=compositor_teardown), \
            patch.dict(app['main'].__globals__, message=lambda text: notices.append(text)):
        notices = []
        app['main'](['wine', 'game.exe'])
        assert not notices, 'clean application exit misreported as launch failure'
    status = root / 'child-status'
    with patch('subprocess.run', return_value=SimpleNamespace(returncode=3)):
        assert app['child'](status, ['false']) == 3
        assert status.read_text() == '3'
    for entry, command in [('rocknix-games.desktop',['rocknix-games']),
                           ('custom.desktop',['rocknix-gamescope','--','wine']),
                           ('terminal.desktop',['foot','-e','command'])]:
        with patch.dict(os.environ, DESKTOP_ENTRY_ID=entry), patch('subprocess.run') as run, \
                patch.dict(app['main'].__globals__, message=lambda text: notices.append(text)):
            notices = []
            app['main'](command)
            run.assert_not_called()
            assert notices
    with patch.dict(os.environ, DESKTOP_ENTRY_ID='rocknix-gamescope.desktop'), \
            patch('os.execv') as execute, patch('subprocess.run') as run:
        app['main'](['rocknix-launcher','gamescope-apps'])
        assert execute.call_args.args[1] == ['rocknix-launcher','gamescope-apps']
        run.assert_not_called()
print('PASS: pinned initial ordering, preserved usage, argv forwarding, failure feedback and recursive launch guards')
