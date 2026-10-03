#!/usr/bin/python3
"""Fresh installation and interrupted resume with real filesystem operations."""
import os
from pathlib import Path
import runpy
import subprocess
import tempfile
from unittest.mock import patch

install = runpy.run_path('payload/bin/rocknix-lxc-install')['install']
storage = runpy.run_path('payload/bin/rocknix-lxc-storage')
for scenario in ('normal', 'ownership-interrupt', 'activation-interrupt', 'collision'):
    with tempfile.TemporaryDirectory() as temporary:
        base = Path(temporary)
        project = base / 'project'
        bundle = project / 'staging/bundle'
        for name in ('rootfs/etc', 'host-tools/usr/bin', 'payload/bin', 'payload/input',
                     'payload/integration', 'payload/systemd', 'payload/guest'):
            (bundle / name).mkdir(parents=True)
        (bundle / 'rootfs/etc/rocknix-desktop-release').write_text('ROCKNIX_LXC_RUNTIME=1\n')
        sizing = bundle / 'payload/guest/rocknix-gamescope'
        sizing.write_bytes(Path('rootfs-overlay/usr/local/bin/rocknix-gamescope').read_bytes())
        app = bundle / 'rootfs/application'
        app.write_text('application')
        identity = app.stat().st_ino
        (bundle / 'host-tools/usr/bin/runtime').write_text('trusted host binary')
        for name in ('preflight', 'rocknix-tools-metadata'):
            (bundle / 'payload/bin' / name).write_text('#!/bin/sh\nexit 0\n')
        (bundle / 'payload/bin/rocknix-device-profile').write_text(
            "def resolve(allow=False): return {'experimental': False}\n"
            "def save_consent(profile, atomic, path): pass\n")
        for name in ('999-rocknix-desktop', 'Desktop Mode.sh'):
            (bundle / 'payload/integration' / name).write_text('/storage/rocknix-desktop/managed/host/bin/example\n')
        (bundle / 'payload/systemd/rocknix-desktop.service').write_bytes(Path('payload/systemd/rocknix-desktop.service').read_bytes())
        for name in ('README.md', 'uninstall.sh', 'upgrade.sh', 'upgrade-lxc.py'):
            (bundle / name).write_text('fixture\n')
        (bundle / 'build-info').write_text('commit=' + 'a' * 40 + '\n')
        api = runpy.run_path('payload/bin/rocknix-lxc-upgrade')
        values = api['install_host'].__globals__
        values['safe_directory'] = lambda path: None  # /tmp test ancestry only
        api['safe_directory'] = values['safe_directory']
        for name in ('UNIT', 'HOOK', 'ENTRY'):
            values[name] = base / 'native' / name
        (base / 'native').mkdir()
        if scenario == 'collision':
            values['UNIT'].write_text('unrelated service')
        journal = project / '.fresh-install.json'
        with patch('subprocess.run') as run:
            if scenario == 'ownership-interrupt':
                with patch.dict(storage, initialize_storage=lambda data: (_ for _ in ()).throw(OSError('fault'))):
                    try:
                        install(bundle, project, api, storage)
                    except OSError:
                        pass
                    else:
                        raise AssertionError('ownership interruption not exercised')
                assert journal.exists() and not (bundle / 'rootfs').exists()
            if scenario == 'activation-interrupt':
                run.side_effect = subprocess.CalledProcessError(1, 'activation')
                try:
                    install(bundle, project, api, storage)
                except subprocess.CalledProcessError:
                    pass
                else:
                    raise AssertionError('activation interruption not exercised')
                assert journal.exists() and (project / 'managed/host/host-tools').exists()
                run.side_effect = None
            if scenario == 'collision':
                try:
                    install(bundle, project, api, storage)
                except RuntimeError:
                    pass
                else:
                    raise AssertionError('unrelated service overwritten')
                assert not journal.exists() and app.exists()
                assert values['UNIT'].read_text() == 'unrelated service'
                continue
            install(bundle, project, api, storage)
        assert not journal.exists()
        host_sizing = project / 'managed/host/guest/rocknix-gamescope'
        assert host_sizing.read_bytes() == sizing.read_bytes()
        assert host_sizing.stat().st_uid == 0 and host_sizing.stat().st_mode & 0o777 == 0o755
        installed = project / 'data/rootfs/application'
        assert installed.stat().st_ino == identity and installed.stat().st_uid == 200000
        assert (project / 'data/home').stat().st_uid == 201000
        assert (bundle / 'host-tools/usr/bin/runtime').exists(), 'resume source was consumed'
        assert (project / 'managed/host/host-tools/usr/bin/runtime').stat().st_uid == 0
        assert str(project / 'managed/host').encode() in values['HOOK'].read_bytes()
print('PASS: fresh separated install, rootfs identity preservation, interruption resume and collision refusal')
