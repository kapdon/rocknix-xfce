#!/usr/bin/env python3
"""Run in LXC: unshare --mount --propagation private python3 THIS [--installed-policy].

Tests the installed mount-aware GLib/GVfs packages as rocknix (UID 1000).
Mapped guest root binds a temporary fstab only inside this private namespace;
--installed-policy validates the production fstab. Read-only share probes also
use private mount isolation. Failed Trash items remain available for recovery.
"""
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import uuid

# The runtime binds only shares that exist on the host. Do not invent host
# directories just to test Trash; exercise every approved share actually bound.
MOUNT_PATHS = {line.split()[4] for line in
               Path('/proc/self/mountinfo').read_text().splitlines()}
SHARES = tuple(name for name in
               ('Desktop', 'Steam', 'backup', 'games-external', 'games-internal')
               if '/storage/' + name in MOUNT_PATHS)


def test_environment(runtime):
    # Start clean: inherited module, loader or D-Bus settings must not make a
    # installed-package test silently exercise a different runtime.
    environment = ['HOME=/home/rocknix', 'USER=rocknix', 'LOGNAME=rocknix',
                   'PATH=/usr/bin:/bin', 'LANG=C.UTF-8', 'GIO_USE_VFS=gvfs',
                   f'XDG_RUNTIME_DIR={runtime}']
    environment.append('XDG_DATA_DIRS=/usr/local/share:/usr/share')
    return environment


def verify_system_packages():
    expected = {
        'libglib2.0-0t64': '2.84.4-3~deb13u5+rocknix1',
        'libglib2.0-bin': '2.84.4-3~deb13u5+rocknix1',
        'gvfs': '1.57.2-2+deb13u1+rocknix1',
        'gvfs-daemons': '1.57.2-2+deb13u1+rocknix1',
        'gvfs-libs': '1.57.2-2+deb13u1+rocknix1',
    }
    for package, version in expected.items():
        actual = subprocess.check_output(
            ['dpkg-query', '-W', '-f=${Status} ${Version}', package], text=True)
        assert actual == 'install ok installed ' + version, (package, actual)
        print(f'Candidate package: {package} {version}', flush=True)


def worker():
    assert os.getuid() == os.getgid() == 1000
    assert Path('/proc/self/uid_map').read_text().split() == ['0', '200000', '65536']
    verify_system_packages()
    gio = '/usr/bin/gio'

    def run(*args, success=True):
        result = subprocess.run([gio, *map(str, args)], text=True,
                                capture_output=True, timeout=20)
        if success:
            assert result.returncode == 0, (args, result.stdout, result.stderr)
        return result

    for name in SHARES:
        share = Path('/storage') / name
        mount_paths = {line.split()[4] for line in
                       Path('/proc/self/mountinfo').read_text().splitlines()}
        # Path.is_mount() compares st_dev and misses same-filesystem binds.
        if str(share) not in mount_paths:
            raise RuntimeError(f'Required shared mount missing: {share}')
        token = uuid.uuid4().hex
        source = share / ('.lxc-trash-probe-' + token)
        payload = 'recoverable fixture ' + token
        collision = 'preserve destination ' + token
        # Exclusive creation, no following a pre-existing symlink.
        with source.open('x') as stream:
            stream.write(payload)
        try:
            run('trash', source)
            assert not source.exists()
            deadline = time.monotonic() + 10
            matches = []
            while time.monotonic() < deadline:
                listing = run('list', '--hidden', '-u', 'trash:///').stdout.splitlines()
                matches = [uri for uri in listing if source.name in uri]
                if matches:
                    break
                time.sleep(.1)
            assert len(matches) == 1, (share, matches)
            uri = matches[0]
            print(f'Trash fixture available for recovery: {uri}', flush=True)
            assert run('cat', uri).stdout == payload
            with source.open('x') as stream:
                stream.write(collision)
            assert run('trash', '--restore', uri, success=False).returncode != 0
            assert source.read_text() == collision
            assert run('cat', uri).stdout == payload
            source.unlink()
            run('trash', '--restore', uri)
            assert source.read_text() == payload
            assert uri not in run('list', '--hidden', '-u', 'trash:///').stdout.splitlines()
            print(f'PASS UID1000 {share}: trash, discovery, read, collision refusal, restore',
                  flush=True)
        finally:
            if source.exists() and not source.is_symlink():
                assert source.read_text() in (payload, collision)
                source.unlink()
            # Never empty Trash or guess/delete a failed restoration's item.


def restart_worker(phase, token):
    assert os.getuid() == os.getgid() == 1000
    assert Path('/proc/self/uid_map').read_text().split() == ['0', '200000', '65536']
    assert uuid.UUID(token).hex == token
    gio = '/usr/bin/gio'
    def run(*args):
        return subprocess.check_output([gio, *map(str, args)], text=True, timeout=20)
    for name in SHARES:
        source = Path('/storage') / name / ('.lxc-trash-restart-' + token)
        payload = 'session recovery fixture ' + name + ' ' + token
        if phase == '--restart-stage':
            with source.open('x') as stream:
                stream.write(payload)
            run('trash', source)
            assert not source.exists()
            print(f'Trashed restart fixture: {source}', flush=True)
        else:
            assert phase == '--restart-recover'
            assert not source.exists() and not source.is_symlink()
            deadline = time.monotonic() + 10
            matches = []
            while time.monotonic() < deadline:
                matches = [uri for uri in run('list', '--hidden', '-u', 'trash:///').splitlines()
                           if source.name in uri and '%5C' + name + '%5C' in uri]
                if matches:
                    break
                time.sleep(.1)
            assert len(matches) == 1, (source, matches)
            assert run('cat', matches[0]) == payload
            run('trash', '--restore', matches[0])
            assert source.is_file() and not source.is_symlink()
            assert source.read_text() == payload
            source.unlink()
            print(f'PASS UID1000 {source.parent}: recovery after private GVfs session restart', flush=True)


def main():
    assert SHARES, 'No shared mounts available for the Trash test'
    args = sys.argv[1:]
    if args == ['--worker']:
        worker()
        return
    if len(args) == 2 and args[0] in ('--restart-stage', '--restart-recover'):
        restart_worker(args[0], args[1])
        return
    if len(args) == 3 and args[0] == '--readonly-worker':
        assert os.getuid() == os.getgid() == 1000
        assert Path('/proc/self/uid_map').read_text().split() == ['0', '200000', '65536']
        source, payload = Path(args[1]), args[2]
        assert source.parent in [Path('/storage') / name for name in SHARES]
        assert source.name.startswith('.lxc-trash-readonly-')
        assert source.read_text() == payload
        result = subprocess.run(['/usr/bin/gio', 'trash', str(source)],
                                text=True, capture_output=True, timeout=20)
        assert result.returncode != 0, (result.stdout, result.stderr)
        assert 'Read-only file system' in result.stderr, result.stderr
        assert source.is_file() and not source.is_symlink()
        assert source.read_text() == payload
        print(f'PASS UID1000 {source.parent}: read-only Trash refused; source unchanged', flush=True)
        return
    installed_policy = args == ['--installed-policy']
    assert not args or installed_policy, 'Expected only --installed-policy'
    assert os.getuid() == 0
    mapping = Path('/proc/self/uid_map').read_text().split()
    assert mapping == ['0', '200000', '65536'], mapping
    # Require caller-created mount isolation; never bind over the live fstab.
    assert os.readlink('/proc/self/ns/mnt') != os.readlink('/proc/1/ns/mnt')
    root_mount = next(line.split() for line in
        Path('/proc/self/mountinfo').read_text().splitlines()
        if line.split()[4] == '/')
    assert not any(field.startswith(('shared:', 'master:'))
                   for field in root_mount[6:root_mount.index('-')])
    with tempfile.TemporaryDirectory(prefix='lxc-trash-device-') as temp:
        base = Path(temp)
        base.chmod(0o755)
        runtime = base / 'runtime'
        runtime.mkdir(mode=0o700)
        os.chown(runtime, 1000, 1000)
        fstab = base / 'fstab'
        fstab.write_text(''.join(f'none /storage/{name} none x-gvfs-trash 0 0\n'
                                 for name in SHARES))
        original_fstab = Path('/etc/fstab').read_bytes()
        if installed_policy:
            for name in SHARES:
                assert f'none /storage/{name} none noauto,x-gvfs-trash 0 0\n'.encode() in original_fstab
        else:
            subprocess.run(['mount', '--bind', str(fstab), '/etc/fstab'], check=True)
        try:
            environment = test_environment(runtime)
            process = subprocess.Popen(['/usr/sbin/runuser', '-u', 'rocknix', '--',
                '/usr/bin/env', '-i', *environment,
                '/usr/bin/dbus-run-session', '--', '/usr/bin/python3',
                str(Path(__file__).resolve()), '--worker'],
                start_new_session=True)
            try:
                assert process.wait(timeout=180) == 0, 'Guest Trash test failed'
            finally:
                # Stop any private-bus helpers still in our isolated group.
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                process.wait(timeout=10)
            token = uuid.uuid4().hex
            print(f'Private session recovery fixture token: {token}', flush=True)
            for phase in ('--restart-stage', '--restart-recover'):
                session = subprocess.Popen(['/usr/sbin/runuser', '-u', 'rocknix', '--',
                    '/usr/bin/env', '-i', *environment,
                    '/usr/bin/dbus-run-session', '--', '/usr/bin/python3',
                    str(Path(__file__).resolve()), phase, token], start_new_session=True)
                try:
                    assert session.wait(timeout=120) == 0, phase
                finally:
                    try:
                        os.killpg(session.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    session.wait(timeout=10)
            # Shadow each real share with a private read-only bind. Do not
            # remount the existing host/shared mount or change production flags.
            for name in SHARES:
                share = Path('/storage') / name
                source = share / ('.lxc-trash-readonly-' + uuid.uuid4().hex)
                payload = 'preserve read-only fixture ' + source.name
                subprocess.run(['/usr/sbin/runuser', '-u', 'rocknix', '--',
                    '/usr/bin/python3', '-c',
                    'import sys; from pathlib import Path; '
                    'p=Path(sys.argv[1]); f=p.open("x"); f.write(sys.argv[2]); f.close()',
                    str(source), payload], check=True)
                bound = False
                try:
                    subprocess.run(['mount', '--bind', str(share), str(share)], check=True)
                    bound = True
                    subprocess.run(['mount', '-o', 'remount,bind,ro', str(share)], check=True)
                    subprocess.run(['/usr/sbin/runuser', '-u', 'rocknix', '--',
                        '/usr/bin/env', '-i', *environment,
                        '/usr/bin/dbus-run-session', '--',
                        '/usr/bin/python3', str(Path(__file__).resolve()),
                        '--readonly-worker', str(source), payload], check=True, timeout=30)
                finally:
                    if bound:
                        subprocess.run(['umount', str(share)], check=True)
                    assert source.is_file() and not source.is_symlink()
                    assert source.read_text() == payload
                    source.unlink()
        finally:
            if installed_policy:
                assert Path('/etc/fstab').read_bytes() == original_fstab
            else:
                subprocess.run(['umount', '/etc/fstab'], check=True)


if __name__ == '__main__':
    main()
