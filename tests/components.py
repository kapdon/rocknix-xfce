#!/usr/bin/python3
"""Component DAG, real packing/assembly, metadata and malicious archive cases."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import tarfile
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
B = runpy.run_path(str(PROJECT / 'scripts/build-components.py'))
C = B['C']


def rejects(fn, *args):
    try:
        fn(*args)
    except (RuntimeError, ValueError):
        return
    raise AssertionError('invalid component input accepted')


def put(archive, name, data=b'fixture', mode=0o755, uid=0, gid=0, link=None):
    item = tarfile.TarInfo(name); item.mode = mode; item.uid = uid; item.gid = gid
    if link:
        item.type = tarfile.SYMTYPE; item.linkname = link
        archive.addfile(item)
    else:
        item.size = len(data); archive.addfile(item, io.BytesIO(data))


with tempfile.TemporaryDirectory(prefix='rocknix-components-test-') as temp:
    work = Path(temp); source = work / 'source'; source.mkdir()
    for name in ('Dockerfile.rootfs', '.dockerignore', 'rootfs-overlay', 'build-support', 'scripts',
                 'payload', 'README.md', 'install.sh', 'install-device.sh', 'uninstall.sh', 'upgrade.sh'):
        path = PROJECT / name
        if path.is_dir():
            shutil.copytree(path, source / name, ignore=shutil.ignore_patterns('__pycache__'))
        else:
            shutil.copy2(path, source / name)
    initial, _ = B['input_keys'](source)
    cases = {
        'rootfs-overlay/etc/xdg/waybar/style.css': {'guest-integration'},
        'payload/bin/rocknix-lxc': {'host-integration'},
        'rootfs-overlay/usr/share/themes/ROCKNIX/gtk-3.0/gtk.css': {'guest-integration', 'host-theme'},
        'build-support/mpv-ffmpeg/build.sh': {'mpv-media'},
        'build-support/trash/mount-identity.h': {'trash-packages', 'guest-base', 'xwayland'},
        'build-support/xwayland/install-image.py': {'xwayland'},
        'build-support/xwayland/check-packages.py': {'guest-base', 'xwayland'},
        'rootfs-overlay/usr/local/bin/rocknix-container-update': {'guest-integration', 'host-integration'},
    }
    for name, expected in cases.items():
        path = source / name; old = path.read_bytes(); path.write_bytes(old + b'\n# changed\n')
        updated, _ = B['input_keys'](source)
        assert {k for k in initial if initial[k] != updated[k]} == expected, name
        path.write_bytes(old)
    config = source / 'rootfs-overlay/etc/xdg/waybar/style.css'
    config.chmod(0o600)
    changed, _ = B['input_keys'](source)
    assert {k for k in initial if initial[k] != changed[k]} == {'guest-integration'}
    config.chmod(0o644)
    lock = source / 'build-support/components/dependencies.json'; old = lock.read_text()
    lock.write_text(old.replace('20261001T000000Z', '20260930T000000Z'))
    updated, _ = B['input_keys'](source)
    assert {k for k in initial if initial[k] != updated[k]} == set(B['DOCKER'])
    lock.write_text(old)
    print('PASS: config/theme/media/package/mode/lock changes invalidate only their dependency branches')

    calls = []
    def export(role, directory, trash=None):
        calls.append(('docker', role))
        raw = directory / 'export.tar'
        with tarfile.open(raw, 'w') as archive:
            if role == 'guest-base':
                put(archive, 'usr/bin/sudo', mode=0o4755)
                for name in 'mount dbus-run-session firefox-esr foot fuzzel glmark2-wayland waybar'.split():
                    put(archive, 'usr/bin/' + name)
                put(archive, 'var/lib/service/data', mode=0o640, uid=101, gid=102)
                put(archive, 'etc/shadow', b'account-data', mode=0o640)
                put(archive, 'etc/xdg/foot/foot.ini', b'Debian default, owned by integration', mode=0o644)
                put(archive, 'etc/ssl/certs/cert-ñ.pem', b'unicode certificate', mode=0o644)
                put(archive, 'bin', link='usr/bin')
            elif role == 'host-runtime':
                for name in 'lxc-start lxc-stop lxc-info lxc-attach slirp4netns mount setfacl getfacl bwrap dbus-run-session xdg-dbus-proxy nm-connection-editor'.split():
                    put(archive, 'usr/bin/' + name)
                for name in ('storage', 'home/rocknix-default'):
                    item = tarfile.TarInfo(name); item.type = tarfile.DIRTYPE; item.mode = 0o755; archive.addfile(item)
                put(archive, 'usr/bin/newuidmap', mode=0o4755)
                put(archive, 'etc/gtk-3.0/settings.ini', b'base theme, owned by host-theme', mode=0o644)
            elif role == 'xwayland':
                put(archive, 'opt/rocknix-xwayland/bin/xwayland-satellite')
                put(archive, 'payload/guest/xwayland-packages.tar', b'offline X11 packages', mode=0o644)
            elif role == 'keyboard':
                put(archive, 'usr/local/bin/wvkbd-rocknix')
            else:
                name = {'firefox-media': 'opt/ffmpeg-rpi-7.1.5', 'mpv-media': 'opt/rocknix-mpv',
                        'fuzzel': 'opt/rocknix-fuzzel'}[role]
                if role in ('firefox-media', 'fuzzel'):
                    put(archive, name + ('/bin/ffmpeg' if role == 'firefox-media' else '/bin/fuzzel'))
                put(archive, name + '/lib/real.so')
                put(archive, name + '/lib/link.so', link='real.so')
        return raw

    packages = work / 'packages'; packages.mkdir(); (packages / 'fixture.deb').write_bytes(b'package-fixture')
    original_run = B['run']
    def run(args, **kwargs):
        if str(args[0]) == 'git':
            return SimpleNamespace(stdout='a' * 40 + '\n')
        calls.append((str(args[0]), [str(arg) for arg in args[1:]]))
        return original_run(args, **kwargs)

    state = B['build'].__globals__
    with patch.dict(state, PROJECT=source, docker_export=export, prepare_trash=lambda _: packages, audit_trash=lambda _: None, run=run):
        store = B['Store'](work / 'store')
        value = B['build'](store, work / 'cold')
        cold_calls = list(calls); calls.clear()
        warm = B['build'](store, work / 'warm')
        assert not calls, calls
        config.write_text(config.read_text() + '\n/* local timing probe */\n')
        new = B['build'](store, work / 'changed')
        assert [entry[0] for entry in calls] == ['xz'], calls
        metrics = json.loads((work / 'changed/timings.json').read_text())
        assert metrics['built'] == ['guest-integration']
        assert not json.loads((work / 'changed/plan.json').read_text())['needs_docker']
        assert all(new['components'][r] == value['components'][r] for r in C['ROLES'] if r != 'guest-integration')
        print('PASS: real orchestrator warm build calls no producer; CSS build runs one small xz, zero Docker calls')
        calls.clear()
        bootstrap = source / 'build-support/components/bootstrap-base.sh'
        old_bootstrap = bootstrap.read_bytes(); bootstrap.write_bytes(old_bootstrap + b'\n# new bootstrap\n')
        with patch.dict(state, prepare_trash=lambda _: (_ for _ in ()).throw(AssertionError('rebuilt cached Trash'))):
            rebuilt = B['build'](store, work / 'bootstrap-change')
        assert [r for program, r in calls if program == 'docker'] == ['guest-base']
        assert rebuilt['components']['trash-packages'] == new['components']['trash-packages']
        bootstrap.write_bytes(old_bootstrap)
        print('PASS: base-only change reuses the verified package transaction without rebuilding Trash')


        # A fresh runner resolves references using only small descriptor downloads.
        remote_cache = work / 'remote-cache'; remote_cache.mkdir()
        remote = B['Store'](remote_cache, 'owner/project')
        remote_assets = {}
        for spec in new['components'].values():
            binding = store.directory / f"{spec['id']}-{spec['input_key']}.json"
            shutil.copyfile(binding, remote_cache / binding.name)
            remote_assets.setdefault(spec['store_tag'], {}).update({
                binding.name: {'digest': 'sha256:' + C['digest'](binding), 'size': binding.stat().st_size},
                spec['asset']: {'digest': 'sha256:' + spec['sha256'], 'size': spec['size']}})
        remote.releases = remote_assets
        with patch.dict(C['fetch'].__globals__, subprocess=SimpleNamespace(run=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError('network download')))):
            resolved = B['build'](remote, work / 'fresh-runner', plan_only=True)
        assert not resolved['missing'] and not resolved['needs_docker']
        assert not list(remote_cache.glob('*.tar.xz'))
        print('PASS: fresh-runner resolution reuses all large assets without downloading them')

    allfiles = {r: store.directory / spec['asset'] for r, spec in new['components'].items()}
    selected = lambda profile: {r: allfiles[r] for r in C['PROFILES'][profile]}
    C['assemble'](new, selected('install'), work / 'install', 'install')
    assembled = work / 'install'
    portal = 'etc/xdg/xdg-desktop-portal/rocknix-portals.conf'
    assert (assembled / 'rootfs' / portal).read_bytes() == (PROJECT / 'rootfs-overlay' / portal).read_bytes()
    assert (assembled / 'rootfs/etc/ssl/certs/cert-ñ.pem').read_bytes() == b'unicode certificate'
    assert (assembled / 'rootfs/usr/bin/sudo').stat().st_mode & 0o7777 == 0o4755
    assert (assembled / 'rootfs/var/lib/service/data').stat().st_uid == 101
    assert (assembled / 'rootfs/var/lib/service/data').stat().st_gid == 102
    assert not (assembled / 'payload/guest/trash-packages.tar').exists()
    assert (assembled / 'rootfs/opt/rocknix-xwayland/bin/xwayland-satellite').is_file()
    assert (assembled / 'payload/guest/xwayland-packages.tar').read_bytes() == b'offline X11 packages'
    C['assemble'](new, selected('update'), work / 'update', 'update')
    assert not (work / 'update/rootfs/etc/shadow').exists()
    assert (work / 'update/payload/guest/trash-packages.tar').exists()
    assert (work / 'update/payload/guest/xwayland-packages.tar').read_bytes() == b'offline X11 packages'
    api = runpy.run_path(str(PROJECT / 'rootfs-overlay/usr/local/bin/rocknix-container-update'))
    baseline = work / 'baseline'
    assert not api['apply'](baseline, work / 'update/desktop-integration.tar.gz')
    assert (baseline / portal).read_bytes() == (PROJECT / 'rootfs-overlay' / portal).read_bytes()
    assert (baseline / 'opt/rocknix-mpv/lib/real.so').exists()
    assert not api['apply'](baseline, work / 'update/desktop-integration.tar.gz')
    assert (baseline / 'opt/rocknix-mpv/lib/real.so').exists()
    print('PASS: fresh/update profiles preserve owners, setuid, links and full managed union; update excludes rootfs seed')
    upgrade = runpy.run_path(str(PROJECT / 'payload/bin/rocknix-lxc-upgrade'))
    release_path = work / 'release.json'; release_path.write_bytes(C['encoded'](new))
    cache = work / 'components'; cache.mkdir()
    for role in C['PROFILES']['update']:
        shutil.copyfile(allfiles[role], cache / allfiles[role].name)
    candidate = work / 'upgrade-candidate'; candidate.mkdir()
    with patch.dict(upgrade['extract'].__globals__,
                    helper_path=lambda _: PROJECT / 'payload/bin/rocknix-components',
                    safe_directory=lambda _: None):
        assert upgrade['extract'](release_path, C['digest'](release_path), candidate) == 'a' * 40
    assert not (candidate / 'rootfs').exists()
    assert (candidate / 'desktop-integration.tar.gz').is_file()
    assert (candidate / 'payload/guest/xwayland-packages.tar').is_file()
    print('PASS: real format-2 upgrade extraction verifies manifest and stages only host/update payloads')


    legacy = copy.deepcopy(new)
    legacy['components'].pop('xwayland')
    C['release'](legacy)
    legacy_files = {r: allfiles[r] for r in C['profile_roles'](legacy, 'update')}
    C['assemble'](legacy, legacy_files, work / 'legacy-update', 'update')
    assert not (work / 'legacy-update/payload/guest/xwayland-packages.tar').exists()
    print('PASS: pre-Xwayland component manifests remain readable')

    bad = copy.deepcopy(new)
    bad['components']['host-integration']['managed'] = copy.deepcopy(new['components']['guest-integration']['managed'])
    rejects(C['release'], bad)
    corrupt = selected('update').copy()
    path = work / 'corrupt.tar.xz'; path.write_bytes(b'not an artifact'); corrupt['keyboard'] = path
    rejects(C['assemble'], new, corrupt, work / 'corrupt-out', 'update')
    assert not (work / 'corrupt-out').exists()
    # Cross-component symlink redirection must fail before extraction.
    hostile_raw = work / 'hostile.tar'
    with tarfile.open(hostile_raw, 'w') as archive:
        put(archive, 'rootfs/etc', link='/tmp/escape')
    hostile = B['compress']('guest-base', 'f' * 64, hostile_raw, store)
    bad = copy.deepcopy(new); bad['components']['guest-base'] = hostile
    files = selected('install'); files['guest-base'] = store.directory / hostile['asset']
    rejects(C['assemble'], bad, files, work / 'hostile-out', 'install')
    assert not (work / 'hostile-out').exists()
    print('PASS: corrupt assets, overlapping inventories and cross-component symlink writes fail before extraction')
