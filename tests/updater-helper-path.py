#!/usr/bin/python3
"""Exercise actual copied-updater helper resolution under fakeroot."""
from pathlib import Path
import runpy
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

source = Path('payload/bin/rocknix-lxc-upgrade').read_bytes()
maintenance = Path('payload/bin/rocknix-desktop-maintenance').read_bytes()
for layout in ('bundle', 'installed', 'payload'):
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        directory = root / ('payload/bin' if layout == 'bundle' else 'bin')
        directory.mkdir(parents=True)
        script = directory / 'rocknix-lxc-upgrade' if layout == 'payload' else root / 'upgrade-lxc.py'
        script.write_bytes(source)
        helper = directory / 'rocknix-install-power'
        helper.write_text('fixture')
        helper.chmod(0o644)
        api = runpy.run_path(str(script))
        locate = api['helper_path']
        # Fixture ancestry is /tmp, unlike root-owned production /storage.
        with patch.dict(locate.__globals__, safe_directory=lambda p: None):
            assert locate('rocknix-install-power') == helper
            helper.chmod(0o666)
            try:
                locate('rocknix-install-power')
                raise AssertionError('writable helper accepted')
            except RuntimeError:
                pass
            helper.unlink()
            helper.symlink_to('/usr/bin/python3')
            try:
                locate('rocknix-install-power')
                raise AssertionError('linked helper accepted')
            except RuntimeError:
                pass
        # Invoke the real idle entry point from every copied-updater location.
        # Its maintenance helper is alongside the other trusted helpers, not
        # alongside the top-level upgrade-lxc.py in bundles/installations.
        guard = directory / 'rocknix-desktop-maintenance'
        guard.write_bytes(maintenance)
        with patch.dict(locate.__globals__, safe_directory=lambda p: None, no_mounts=lambda p: None), \
                patch('subprocess.run', return_value=SimpleNamespace(stdout='inactive\n', returncode=0)), \
                patch('os.path.lexists', return_value=False):
            api['idle']()
        with patch.dict(locate.__globals__, safe_directory=lambda p: None), \
                patch('os.path.lexists', side_effect=lambda p: str(p) == '/run/rocknix-desktop-games/session.json'), \
                patch('subprocess.run') as run:
            try:
                api['idle']()
                raise AssertionError('copied updater ignored unfinished game recovery')
            except RuntimeError as error:
                assert 'Steam session recovery' in str(error)
            run.assert_not_called()
print('PASS: bundled, installed and payload updater helper paths; unsafe helper refusal')
