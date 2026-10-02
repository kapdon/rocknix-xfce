#!/usr/bin/env python3
"""Candidate package preparation guards; no builds or host package changes."""
from pathlib import Path
import io
import runpy
import subprocess
import sys
import tarfile
import tempfile
from unittest.mock import patch

repo = Path(__file__).resolve().parents[1]
api = runpy.run_path(str(repo / 'build-support/trash/prepare-package.py'))
main = api['main']
state = main.__globals__


def exercise(kind='glib', version='2.84.4-3~deb13u5', name='glib2.0',
             fmt='3.0 (quilt)', existing=False, expected_failure=False):
    with tempfile.TemporaryDirectory() as temporary:
        tree = Path(temporary)
        (tree / 'debian/source').mkdir(parents=True)
        (tree / 'debian/patches').mkdir()
        (tree / 'debian/source/format').write_text(fmt)
        if existing:
            (tree / 'debian/patches/rocknix-mount-aware-trash.patch').touch()
        calls = []

        def fake_run(*args, **kwargs):
            calls.append(args)
            if args[:2] == ('dpkg-parsechangelog', '--show-field'):
                return version if args[2] == 'Version' else name
            return ''

        expected = '2.84.4-3~deb13u5' if kind == 'glib' else '1.57.2-2+deb13u1'
        with patch.dict(state, run=fake_run), patch.object(
                sys, 'argv', ['prepare-package.py', kind, str(tree), expected]):
            try:
                main()
            except SystemExit:
                assert expected_failure, calls
                # Only read-only metadata commands are allowed before refusal.
                assert all(call[0] == 'dpkg-parsechangelog' for call in calls)
            else:
                assert not expected_failure, calls
                assert [call[0] for call in calls] == [
                    'dpkg-parsechangelog', 'dpkg-parsechangelog', 'dpkg-source',
                    sys.executable, 'dpkg-source', 'dch', 'dpkg']
                assert calls[4] == ('dpkg-source', '--commit', '.',
                                    'rocknix-mount-aware-trash.patch')
                assert calls[5][2] == version + '+rocknix1'


exercise()
exercise(kind='gvfs', version='1.57.2-2+deb13u1', name='gvfs')
exercise(version='2.84.4-3~deb13u6', expected_failure=True)
exercise(version='2.84.4-3~deb13u5+rocknix1', expected_failure=True)
exercise(name='other', expected_failure=True)
exercise(fmt='3.0 (native)', expected_failure=True)
exercise(existing=True, expected_failure=True)
print('PASS: package preparation order and pre-edit source/version/format guards')

# Source exports must precede compilation: debhelper leaves binary staging
# trees that dpkg-source must reject, not silently include in the source tar.
dockerfile = (repo / 'build-support/trash/Dockerfile.packages').read_text()
builder_stage = dockerfile.split('FROM sources AS builder\n', 1)[1].split('FROM scratch AS artifact', 1)[0]
assert builder_stage.index('USER builder\n') < builder_stage.index('RUN python3')
assert 'USER root' not in builder_stage
assert 'ENV HOME=/home/builder USER=builder LOGNAME=builder' in builder_stage
assert dockerfile.count('useradd --create-home --uid 1000') == 1
assert 'chown -R builder:builder /build /artifacts' in dockerfile
print('PASS: Docker package compilation uses an ordinary Debian builder')
for component in ('glib', 'gvfs'):
    step = dockerfile.split('RUN python3 /patch/prepare-package.py ' + component, 1)[1].split('\nRUN ', 1)[0]
    assert step.index('dpkg-source -b .') < step.index('dpkg-buildpackage -us')
print('PASS: source packages exported before binary staging in both package builds')

device = runpy.run_path(str(repo / 'tests/device/check-trash.py'))
environment = device['test_environment'](Path('/tmp/private-runtime'))
assert not any(item.startswith(('LD_', 'GIO_MODULE_DIR=', 'GIO_EXTRA_MODULES=',
                                'DBUS_SESSION_BUS_ADDRESS=')) for item in environment)
assert not any('/opt/' in item for item in environment)
assert 'GIO_USE_VFS=gvfs' in environment
assert 'HOME=/home/rocknix' in environment
print('PASS: installed-package probe has no private loader/module overrides')

package_api = runpy.run_path(str(repo / 'build-support/trash/check-packages.py'))
audit = package_api['audit_payload']
assert package_api['source_name']('gvfs', '') == 'gvfs'
assert package_api['source_name']('libglib2.0-bin', 'glib2.0 (2.84.4)') == 'glib2.0'


def payload_case(name='usr/bin/gio', uid=0, machine=183, duplicate=False, denied=False,
                 kind=tarfile.REGTYPE, elf=True):
    data = io.BytesIO()
    header = b'\x7fELF\x02\x01' + bytes(12) + machine.to_bytes(2, 'little')
    if not elf:
        header = b'not an ELF program'
    with tarfile.open(fileobj=data, mode='w') as archive:
        for _ in range(2 if duplicate else 1):
            member = tarfile.TarInfo(name)
            member.uid = uid
            member.type = kind
            if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
                member.linkname = 'other-file'
            member.size = len(header)
            archive.addfile(member, io.BytesIO(header))
    data.seek(0)
    with tarfile.open(fileobj=data, mode='r|') as archive:
        try:
            paths, elves = audit(archive, {'usr/bin/gio'})
        except ValueError:
            assert denied
        else:
            assert not denied
            assert paths == {name} and elves == 1


payload_case()
payload_case(name='../escape', denied=True)
payload_case(name='/absolute', denied=True)
payload_case(name='opt/unmanaged/libgio.so', denied=True)
payload_case(name='etc/apt/preferences.d/pin', denied=True)
payload_case(name='etc/ld.so.conf.d/private.conf', denied=True)
payload_case(uid=1000, denied=True)
payload_case(machine=62, denied=True)
payload_case(duplicate=True, denied=True)
payload_case(kind=tarfile.DIRTYPE, denied=True)
payload_case(kind=tarfile.SYMTYPE, denied=True)
payload_case(kind=tarfile.LNKTYPE, denied=True)
payload_case(elf=False, denied=True)
print('PASS: payload audit rejects unsafe paths, overrides, owners and wrong ELF architecture')
print('PASS: required programs cannot be substituted by directories, links or non-ELF files')

installer = runpy.run_path(str(repo / 'build-support/trash/install-image.py'))
for fails in (False, True):
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        if fails and command[0] == 'apt-get':
            raise subprocess.CalledProcessError(100, command)

    with patch('subprocess.check_output', return_value='gvfs-common\nunrelated\n'), patch('subprocess.run', side_effect=fake_run):
        try:
            installer['install_preserving_marks'](['apt-get', 'install', '/tmp/package.deb'], {'gvfs-common', 'gvfs'})
        except subprocess.CalledProcessError:
            assert fails
        else:
            assert not fails
    assert calls == [['apt-get', '-y', 'install', '/tmp/package.deb'],
                     ['apt-mark', 'auto', 'gvfs-common']]
print('PASS: automatic package flags restored after successful and failed installation')
plan = installer['validate_plan']
assert plan('Inst gvfs [old] (new Debian)\nConf gvfs (new Debian)') == {'gvfs'}
assert plan('0 upgraded, 0 newly installed') == set()
assert plan('Conf gvfs:arm64 (new Debian)') == set()
for invalid in ('Remv gvfs [old]', 'Purg gvfs', 'Inst unrelated (1.0 Debian)',
                'Conf unrelated (1.0 Debian)', 'Conf unrelated:arm64 (1.0 Debian)'):
    try:
        plan(invalid)
    except RuntimeError:
        pass
    else:
        raise AssertionError(invalid)
with tempfile.TemporaryDirectory() as temporary:
    directory = Path(temporary)
    try:
        installer['runtime_paths'](directory)
    except RuntimeError:
        pass
    else:
        raise AssertionError('missing runtime packages accepted')
install_source = (repo / 'build-support/trash/install-image.py').read_text()
assert "'--no-remove', '--no-install-recommends', 'install'" in install_source
rootfs_docker = (repo / 'Dockerfile.rootfs').read_text()
assert 'RUN --network=none --mount=from=trash-package-inputs' in rootfs_docker
assert rootfs_docker.index('sudo python3') < rootfs_docker.index('python3 /tmp/trash-tools/check-packages.py')
assert "'gt', wanted" in install_source
assert '--allow-downgrades' not in install_source
print('PASS: image package plan rejects removals, unrelated changes and missing candidates')
