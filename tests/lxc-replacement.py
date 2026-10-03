#!/usr/bin/python3
"""Real filesystem switches and restart recovery with home identity sentinels."""
from pathlib import Path
import runpy
import tempfile
from unittest.mock import patch

U = runpy.run_path('payload/bin/rocknix-lxc-upgrade')
R = runpy.run_path('payload/bin/rocknix-lxc-replace')

for fault in ('prepared', 'before-rename', 'old-moved', 'new-moved', 'host-changed', 'committed'):
    with tempfile.TemporaryDirectory() as temporary:
        project = Path(temporary)
        host, data = project / 'host', project / 'data'
        state, home, root = host / 'state', data / 'home', data / 'rootfs'
        for path in (state, home, root, project / 'native'):
            path.mkdir(parents=True, exist_ok=True)
        (home / 'save-game').write_bytes(b'user content')
        (home / 'save-link').symlink_to('save-game')
        home_stat = home.stat()
        save_stat = (home / 'save-game').stat()
        (root / 'old-app').write_text('discard on success')
        old_identity = R['identity'](root)
        (host / 'build-info').write_text('old revision')
        (host / 'bin').mkdir()
        (host / 'bin/launcher').write_text('old launcher')
        (state / 'native-providers').write_text('graphics')
        work = state / 'upgrade-lxc.fixture'; work.mkdir()
        (work / 'rootfs').mkdir()
        (work / 'rootfs/new-app').write_text('new app')
        (work / 'host-tools').mkdir()
        api = dict(U, BASE=host, ROOTFS=root, WORKSPACE=state,
                   GUARD=state / 'upgrade-in-progress.json',
                   safe_directory=lambda _: None, no_mounts=lambda _: None)
        for name in ('UNIT', 'HOOK', 'ENTRY'):
            api[name] = project / 'native' / name
        api['UNIT'].write_text('old service')
        api['HOOK'].write_text('old hook')
        def remove(path):
            assert path.parent == state and path.name.startswith('upgrade-lxc.')
            U['shutil'].rmtree(path)
        api['remove_stage'] = remove
        with patch.dict(U['atomic'].__globals__, safe_directory=lambda _: None), \
             patch('subprocess.run'), patch('os.sync'):
            txn = R['Replacement'](api)
            txn.prepare(work, 'a' * 64, 'b' * 40)
            if fault != 'prepared':
                txn.save('activating')
            if fault in ('old-moved', 'new-moved', 'host-changed', 'committed'):
                root.rename(work / 'previous-rootfs')
            if fault in ('new-moved', 'host-changed', 'committed'):
                (work / 'rootfs').rename(root)
            if fault in ('host-changed', 'committed'):
                (host / 'bin/launcher').write_text('new launcher')
                (host / 'bin/new-helper').write_text('new helper')
                api['UNIT'].write_text('new service')
                api['ENTRY'].write_text('new entry')
            if fault == 'committed':
                txn.save('committed')
            # Simulate a new updater process after power loss at each boundary.
            recovered = R['Replacement'](api)
            try:
                recovered.load('c' * 64)
                raise AssertionError('wrong artifact accepted')
            except RuntimeError:
                pass
            assert recovered.load('a' * 64)
            recovered.rollback()
            recovered.rollback()  # Recovery itself is repeatable.
            recovered.finish()
        assert not work.exists() and not api['GUARD'].exists()
        assert R['identity'](home) == [home_stat.st_dev, home_stat.st_ino]
        actual = (home / 'save-game').stat()
        assert (actual.st_ino, actual.st_uid, actual.st_gid, actual.st_mode) == (
            save_stat.st_ino, save_stat.st_uid, save_stat.st_gid, save_stat.st_mode)
        assert (home / 'save-game').read_bytes() == b'user content'
        assert (home / 'save-link').is_symlink()
        assert (state / 'native-providers').read_text() == 'graphics'
        if fault == 'committed':
            assert (root / 'new-app').exists() and not (root / 'old-app').exists()
            assert api['UNIT'].read_text() == 'new service'
        else:
            assert R['identity'](root) == old_identity
            assert (host / 'bin/launcher').read_text() == 'old launcher'
            assert not (host / 'bin/new-helper').exists()
            assert api['UNIT'].read_text() == 'old service'
            assert not api['ENTRY'].exists()
print('PASS: replacement interruption recovery, host/rootfs rollback and home inode/metadata preservation')
