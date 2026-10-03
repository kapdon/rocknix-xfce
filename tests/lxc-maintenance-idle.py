#!/usr/bin/python3
"""Maintenance must fail closed while Desktop starts or stops; no host actions."""
from pathlib import Path
import runpy
import subprocess
from types import SimpleNamespace
from unittest.mock import patch

for script, function in (
        ('rocknix-lxc-upgrade', 'idle'),
        ('rocknix-desktop-maintenance', 'require_idle')):
    idle = runpy.run_path('payload/bin/' + script)[function]
    for state in ('inactive', 'active', 'activating', 'deactivating',
                  'reloading', 'failed', '', 'unknown'):
        def run(args, **kwargs):
            if args[1] == 'show':
                if args[-1] in ('rocknix-desktop-games.service','steam-bigpicture.scope'):
                    return SimpleNamespace(stdout='inactive\n',returncode=0)
                assert args == ['systemctl', 'show', '--property=ActiveState',
                                '--value', 'rocknix-desktop.service']
                assert kwargs == dict(capture_output=True, text=True, check=True)
                return SimpleNamespace(stdout=state + '\n', returncode=0)
            assert state == 'inactive', 'continued checks despite unsafe Desktop state'
            return SimpleNamespace(returncode=0)

        with patch('subprocess.run', side_effect=run), \
                patch.dict(idle.__globals__, no_mounts=lambda path: None), \
                patch('os.path.lexists', return_value=False), \
                patch.object(Path, 'glob', return_value=[]):
            try:
                idle()
            except RuntimeError:
                assert state != 'inactive'
            else:
                assert state == 'inactive', (script, state)

    with patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, 'systemctl')):
        try:
            idle()
        except subprocess.CalledProcessError:
            pass
        else:
            raise AssertionError('systemctl failure was treated as idle')

    # Even between supervisor exit and Desktop return, the native scope or
    # durable journal must prevent an updater taking over the installation.
    for unit in ('rocknix-desktop-games.service','steam-bigpicture.scope'):
        for state in ('active','activating','deactivating',''):
            def run(args, **kwargs):
                return SimpleNamespace(stdout=(state if args[-1]==unit else 'inactive')+'\n',returncode=0)
            with patch('subprocess.run',side_effect=run),patch('os.path.lexists',return_value=False):
                try:idle()
                except RuntimeError:pass
                else:raise AssertionError((script,unit,state))
    with patch('os.path.lexists',side_effect=lambda p: str(p)=='/run/rocknix-desktop-games/session.json'),patch('subprocess.run') as run:
        try:idle()
        except RuntimeError:pass
        else:raise AssertionError('unfinished game recovery accepted')
        run.assert_not_called()

print('LXC maintenance requires confirmed inactive Desktop: PASS')
