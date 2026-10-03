#!/usr/bin/python3
"""Resolve immutable artifacts before Docker; build and compress only misses."""
import argparse
import ast
import copy
from datetime import datetime, timezone
import hashlib
import io
import json
import os
import platform
from pathlib import Path
import re
import runpy
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time

PROJECT = Path(__file__).resolve().parents[1]
C = runpy.run_path(str(PROJECT / 'payload/bin/rocknix-components'))
ROOT_STAGES = {
    'guest-base': ('trash-package-inputs', 'desktop-dependencies', 'guest-base'),
    'firefox-media': ('ffmpeg-cross-builder', 'ffmpeg-rpi-builder', 'firefox-component'),
    'mpv-media': ('ffmpeg-cross-builder', 'mpv-ffmpeg-builder', 'mpv-component'),
    'keyboard': ('keyboard-builder', 'keyboard-component'),
    'xwayland': ('xwayland-builder', 'xwayland-component'),
}
DOCKER = {'xwayland': ('Dockerfile.rootfs', 'xwayland-component'),
          'guest-base': ('Dockerfile.rootfs', 'guest-base'),
          'host-runtime': ('build-support/lxc/Dockerfile.host-tools', 'host-runtime'),
          'firefox-media': ('Dockerfile.rootfs', 'firefox-component'),
          'mpv-media': ('Dockerfile.rootfs', 'mpv-component'),
          'keyboard': ('Dockerfile.rootfs', 'keyboard-component'),
          'fuzzel': ('build-support/fuzzel/Dockerfile', 'artifact'),
          'trash-packages': ('build-support/trash/Dockerfile.packages', 'artifact')}


def run(args, **kwargs):
    return subprocess.run([str(x) for x in args], check=True, **kwargs)


def docker_stages(text):
    result = {}
    for block in re.split(r'(?m)(?=^FROM )', text)[1:]:
        match = re.search(r'(?im)^FROM .+ AS ([\w-]+)\s*$', block)
        if not match:
            raise RuntimeError('every component Docker stage must be named')
        result[match[1]] = block
    return result


def paths(root, selected):
    result = {}
    for name in selected:
        path = root / name
        if not path.exists() and not path.is_symlink():
            raise RuntimeError('missing component input: ' + name)
        for item in ([path] + sorted(path.rglob('*')) if path.is_dir() else [path]):
            if '__pycache__' in item.parts or item.suffix == '.pyc':
                continue
            relative = item.relative_to(root).as_posix()
            info = item.lstat()
            if item.is_symlink():
                result[relative] = {'link': os.readlink(item)}
            elif item.is_file():
                result[relative] = {'sha256': C['digest'](item), 'mode': stat.S_IMODE(info.st_mode)}
            elif item.is_dir():
                result[relative] = {'directory': stat.S_IMODE(info.st_mode)}
            else:
                raise RuntimeError('special component input')
    return result


def input_keys(root=None):
    root = PROJECT if root is None else root
    lock = json.loads((root / 'build-support/components/dependencies.json').read_text())
    if (lock.get('format') != 1 or lock.get('platform') != 'linux/arm64' or
            not re.fullmatch(r'\d{8}T\d{6}Z', lock.get('debian_snapshot', '')) or
            lock.get('runtime_abi') != C['ABI']):
        raise RuntimeError('unsupported component dependency lock')
    recipe = paths(root, ['scripts/build-components.py', 'payload/bin/rocknix-components'])
    selected = {
        'guest-base': ['build-support/components/bootstrap-base.sh',
                       'build-support/trash/check-packages.py', 'build-support/trash/install-image.py',
                       'rootfs-overlay/usr/local/bin/rocknix-default-password',
                       'rootfs-overlay/etc/systemd/system/rocknix-desktop-session.service'],
        'host-runtime': [],
        'firefox-media': ['build-support/ffmpeg/build.sh'],
        'mpv-media': ['build-support/mpv-ffmpeg'],
        'keyboard': ['build-support/wvkbd'],
        'xwayland': ['build-support/xwayland'],
        'fuzzel': ['build-support/fuzzel'],
        'trash-packages': ['build-support/trash', 'scripts/package-trash.py', 'payload/guest/update-trash-packages.py'],
        'guest-integration': ['rootfs-overlay'],
        'host-integration': ['payload', 'install.sh', 'install-device.sh', 'uninstall.sh',
                             'upgrade.sh', 'README.md', 'rootfs-overlay/usr/local/bin/rocknix-container-update',
                             'rootfs-overlay/usr/local/bin/rocknix-gamescope'],
        'host-theme': ['rootfs-overlay/etc/gtk-3.0/settings.ini', 'rootfs-overlay/usr/share/themes/ROCKNIX'],
    }
    root_stages = docker_stages((root / 'Dockerfile.rootfs').read_text())
    host_stages = docker_stages((root / 'build-support/lxc/Dockerfile.host-tools').read_text())
    keys, inputs = {}, {}
    for role in ('trash-packages', *[x for x in C['ROLES'] if x != 'trash-packages']):
        data = {'role': role, 'platform': 'linux/arm64', 'recipe': recipe, 'files': paths(root, selected[role])}
        if role in DOCKER:
            data['dependencies'] = lock
            data['context_rules'] = paths(root, ['.dockerignore'])
            data['docker_frontend'] = (root / DOCKER[role][0]).read_text().split('FROM ', 1)[0]
        if role in ('firefox-media', 'mpv-media', 'keyboard', 'fuzzel', 'xwayland'):
            data['build_architecture'] = platform.machine()
        if role in ROOT_STAGES:
            data['docker'] = {stage: root_stages[stage] for stage in ROOT_STAGES[role]}
        elif role == 'host-runtime':
            data['docker'] = host_stages['host-runtime']
        if role == 'trash-packages' and os.environ.get('ROCKNIX_TRASH_PACKAGES_DIR'):
            # A local native override must never masquerade as the locked CI
            # build. Hash audited bytes, excluding volatile export attestations.
            directory = Path(os.environ['ROCKNIX_TRASH_PACKAGES_DIR'])
            data['native_override'] = paths(directory, [p.name for p in directory.iterdir()
                if p.name != 'provenance.json'])
        if role == 'guest-base':
            data['trash_packages'] = keys['trash-packages']
        if role == 'guest-base':
            # Ownership policy, not configuration contents, determines what the
            # base must omit. New files in an existing namespace remain cheap.
            policy_source = (root / 'rootfs-overlay/usr/local/bin/rocknix-container-update').read_text()
            updater = ast.parse(policy_source)
            policy = [node for node in updater.body if
                      isinstance(node, ast.FunctionDef) and node.name == 'allowed' or
                      isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and
                          t.id in ('CONFIG', 'IDENTITY') for t in node.targets)]
            # AST dump formatting differs across Python 3.12/3.14. Source
            # segments keep keys portable between developer and CI machines.
            data['managed_namespace'] = [ast.get_source_segment(policy_source, node) for node in policy]
        keys[role] = hashlib.sha256(C['encoded'](data)).hexdigest()
        inputs[role] = data
    return keys, inputs


class Store:
    """Local cache is disposable. Release assets are the durable authority."""
    def __init__(self, directory, repository=None):
        self.directory, self.repository = Path(directory), repository
        self.directory.mkdir(parents=True, exist_ok=True)
        self.releases = {}

    def asset_list(self, tag):
        if tag not in self.releases:
            result = subprocess.run(['gh', 'api', f'repos/{self.repository}/releases/tags/{tag}'],
                                    capture_output=True, text=True)
            if result.returncode:
                if '(HTTP 404)' in result.stderr:
                    self.releases[tag] = {}
                else:
                    raise RuntimeError('cannot inspect component store: ' + result.stderr)
            else:
                value = json.loads(result.stdout)
                self.releases[tag] = {item['name']: item for item in value['assets'] if item['state'] == 'uploaded'}
        return self.releases[tag]

    def find(self, role, key):
        tag = 'components-v1-' + key[:3]
        name = f'{role}-{key}.json'
        binding = self.directory / name
        if self.repository:
            assets = self.asset_list(tag)
            if name not in assets:
                return None
            item = assets[name]
            expected = item.get('digest', '').removeprefix('sha256:')
            if not C['HEX'].fullmatch(expected):
                raise RuntimeError('component binding lacks remote digest')
            C['fetch'](self.repository, tag, name, binding, expected, item['size'])
        elif not binding.exists():
            return None
        spec = C['descriptor'](json.loads(binding.read_text()), role, key)
        if self.repository:
            item = assets.get(spec['asset'])
            if not item or item['size'] != spec['size'] or item.get('digest') != 'sha256:' + spec['sha256']:
                raise RuntimeError('published component is missing or corrupt')
        else:
            blob = self.directory / spec['asset']
            if not blob.exists():
                return None
            if blob.stat().st_size != spec['size'] or C['digest'](blob) != spec['sha256']:
                raise RuntimeError('local component cache is corrupt')
        return spec

    def blob(self, spec):
        path = self.directory / spec['asset']
        if self.repository:
            C['fetch'](self.repository, spec['store_tag'], spec['asset'], path, spec['sha256'], spec['size'])
        if path.stat().st_size != spec['size'] or C['digest'](path) != spec['sha256']:
            raise RuntimeError('component artifact verification failed')
        return path


def locked_dockerfile(source, snapshot):
    lines = []
    for line in source.splitlines():
        lines.append(line)
        if line.startswith('FROM ') and 'debian@sha256:' in line:
            lines.append('RUN sed -i ' + "'s|http://deb.debian.org/debian-security|http://snapshot.debian.org/archive/debian-security/" + snapshot + "/|g; " +
                         's|http://deb.debian.org/debian|http://snapshot.debian.org/archive/debian/' + snapshot + "/|g' /etc/apt/sources.list.d/debian.sources " +
                         "&& printf 'Acquire::Check-Valid-Until \"false\";\\n' > /etc/apt/apt.conf.d/99snapshot")
    return '\n'.join(lines) + '\n'


def docker_export(role, work, trash=None):
    source, target = DOCKER[role]
    lock = json.loads((PROJECT / 'build-support/components/dependencies.json').read_text())
    recipe = work / 'Dockerfile'
    recipe.write_text(locked_dockerfile((PROJECT / source).read_text(), lock['debian_snapshot']))
    raw = work / 'export.tar'
    command = ['docker', 'buildx', 'build', '--platform', 'linux/arm64', '--file', recipe,
               '--target', target, '--provenance=false']
    if os.environ.get('ACTIONS_CACHE_URL') or os.environ.get('ACTIONS_RESULTS_URL'):
        command += ['--cache-from', f'type=gha,version=2,scope=component-{role}',
                    '--cache-to', f'type=gha,version=2,scope=component-{role},mode=max']
    if trash:
        command += ['--build-context', f'trash-packages={trash}']
    empty = work / 'empty'; empty.mkdir(exist_ok=True)
    if source == 'Dockerfile.rootfs':
        command += ['--build-context', f'fuzzel-artifacts={empty}']
        if not trash:
            command += ['--build-context', f'trash-packages={empty}']
    context = PROJECT / 'build-support/trash' if role == 'trash-packages' else PROJECT
    if role in ('guest-base', 'host-runtime'):
        iid = work / 'iid'
        run(command + ['--load', '--iidfile', iid, context])
        identity = iid.read_text().strip()
        if not re.fullmatch('sha256:[0-9a-f]{64}', identity):
            raise RuntimeError('invalid immutable image ID')
        container = run(['docker', 'create', '--platform', 'linux/arm64', identity, '/bin/true'],
                        capture_output=True, text=True).stdout.strip()
        try:
            with raw.open('wb') as output:
                run(['docker', 'export', container], stdout=output)
        finally:
            run(['docker', 'rm', '-f', container], stdout=subprocess.DEVNULL)
    else:
        run(command + ['--output', f'type=tar,dest={raw}', context])
    return raw


def add_bytes(archive, name, data, mode=0o644):
    member = tarfile.TarInfo(name); member.size = len(data); member.mode = mode
    archive.addfile(member, io.BytesIO(data))


def add_tree(archive, source, prefix, exclude=()):
    source = Path(source)
    for path in sorted(source.rglob('*')):
        name = path.relative_to(source).as_posix()
        if '__pycache__' in path.parts or path.suffix == '.pyc' or name in exclude:
            continue
        archive.inodes.clear()
        item = archive.gettarinfo(str(path), arcname=prefix + name)
        item.uid = item.gid = 0; item.uname = item.gname = ''; item.mtime = 0
        if prefix == 'rootfs/' and name.startswith('usr/local/bin/') and item.isfile():
            item.mode = 0o755
        with path.open('rb') if item.isfile() else io.BytesIO() as stream:
            archive.addfile(item, stream if item.isfile() else None)


def payload_tar(role, work, raw=None, trash=None):
    result = work / 'payload.tar'
    guest = runpy.run_path(str(PROJECT / 'rootfs-overlay/usr/local/bin/rocknix-container-update'))
    with tarfile.open(result, 'w') as archive:
        if raw:
            prefix = 'host-tools/' if role == 'host-runtime' else 'rootfs/'
            with tarfile.open(raw) as source:
                for original in source:
                    item = copy.copy(original)
                    # Exported Unicode names may carry PAX path/linkpath keys.
                    # Regenerate those keys after adding the component prefix.
                    item.pax_headers = {key: value for key, value in original.pax_headers.items()
                                        if key not in ('path', 'linkpath')}
                    name = item.name.removeprefix('./').rstrip('/')
                    if not name or name == '.' or name == '.dockerenv' or name == 'provenance.json':
                        continue
                    if role == 'host-runtime' and not item.isdir() and C['owns']('host-theme', 'host-tools/' + name):
                        continue
                    if role == 'guest-base':
                        if not item.isdir() and guest['allowed'](name):
                            continue
                        if name in ('etc/resolv.conf', 'etc/hosts', 'etc/hostname',
                                    'etc/systemd/system/rocknix-desktop-session.service'):
                            continue
                        if any(name.startswith(p + '/') for p in ('dev', 'proc', 'run', 'sys', 'tmp')):
                            continue
                    item.name = prefix + name
                    if item.islnk():
                        item.linkname = prefix + item.linkname.removeprefix('./')
                    archive.addfile(item, source.extractfile(original) if item.isfile() else None)
            if role == 'guest-base':
                add_bytes(archive, 'rootfs/etc/resolv.conf', b'')
                add_bytes(archive, 'rootfs/etc/hostname', b'rocknix-desktop\n')
                add_bytes(archive, 'rootfs/etc/hosts', b'127.0.0.1 localhost\n127.0.1.1 rocknix-desktop\n::1 localhost ip6-localhost ip6-loopback\n')
        elif role == 'guest-integration':
            add_tree(archive, PROJECT / 'rootfs-overlay', 'rootfs/', ('usr/sbin/policy-rc.d', 'etc/rocknix-desktop-release'))
            release = (PROJECT / 'rootfs-overlay/etc/rocknix-desktop-release').read_bytes()
            add_bytes(archive, 'rootfs/etc/rocknix-desktop-release', release + b'ROCKNIX_LXC_RUNTIME=1\n')
            add_bytes(archive, 'rootfs/etc/systemd/journald.conf.d/rocknix-container.conf',
                      b'[Journal]\nStorage=volatile\nRuntimeMaxUse=32M\n')
            for name in ('return', 'keyboard', 'about'):
                asset = 'rocknix-' + name + '.desktop'
                add_bytes(archive, 'rootfs/home/rocknix-default/Desktop/' + asset,
                          (PROJECT / 'rootfs-overlay/usr/share/applications' / asset).read_bytes(), 0o755)
        elif role == 'host-theme':
            add_bytes(archive, 'host-tools/etc/gtk-3.0/settings.ini',
                      (PROJECT / 'rootfs-overlay/etc/gtk-3.0/settings.ini').read_bytes())
            add_tree(archive, PROJECT / 'rootfs-overlay/usr/share/themes/ROCKNIX', 'host-tools/usr/share/themes/ROCKNIX/')
        elif role == 'host-integration':
            add_tree(archive, PROJECT / 'payload', 'payload/')
            for name in sorted(C['TOP_FILES'] - {'upgrade-lxc.py'}):
                path = PROJECT / name
                add_bytes(archive, name, path.read_bytes(), stat.S_IMODE(path.stat().st_mode))
            add_bytes(archive, 'upgrade-lxc.py', (PROJECT / 'payload/bin/rocknix-lxc-upgrade').read_bytes(), 0o755)
            add_bytes(archive, 'payload/guest/rocknix-container-update',
                      (PROJECT / 'rootfs-overlay/usr/local/bin/rocknix-container-update').read_bytes(), 0o755)
            add_bytes(archive, 'payload/guest/rocknix-gamescope',
                      (PROJECT / 'rootfs-overlay/usr/local/bin/rocknix-gamescope').read_bytes(), 0o755)
        elif role == 'trash-packages':
            packages = work / 'packages.tar'
            run([sys.executable, PROJECT / 'scripts/package-trash.py', trash, packages])
            item = tarfile.TarInfo('payload/guest/trash-packages.tar')
            item.size = packages.stat().st_size; item.mode = 0o644
            with packages.open('rb') as stream:
                archive.addfile(item, stream)
        else:
            raise RuntimeError('unknown component producer')
    return result



def check_payload(role, path):
    required = {
        'guest-base': ['rootfs/usr/bin/' + name for name in
                       'mount dbus-run-session firefox-esr foot fuzzel glmark2-wayland waybar sudo'.split()],
        'host-runtime': ['host-tools/usr/bin/' + name for name in
                         'lxc-start lxc-stop lxc-info lxc-attach slirp4netns mount setfacl getfacl bwrap dbus-run-session xdg-dbus-proxy nm-connection-editor'.split()],
        'firefox-media': ['rootfs/opt/ffmpeg-rpi-7.1.5/bin/ffmpeg'],
        'fuzzel': ['rootfs/opt/rocknix-fuzzel/bin/fuzzel'],
        'keyboard': ['rootfs/usr/local/bin/wvkbd-rocknix'],
        'xwayland': ['rootfs/opt/rocknix-xwayland/bin/xwayland-satellite'],
    }
    with tarfile.open(path) as archive:
        rows = archive.getmembers()
        members = {item.name: item for item in rows}
        if len(members) != len(rows):
            raise RuntimeError('duplicate component producer path')
        for name, item in members.items():
            if not C['safe_name'](name) or (not item.isdir() and not C['owns'](role, name)):
                raise RuntimeError('component producer path outside role: ' + name)
        for name in required.get(role, []):
            item = members.get(name)
            if not item or not item.mode & 0o111 or not (item.isfile() or item.islnk() or item.issym()):
                raise RuntimeError('component lacks required executable: ' + name)
        if role == 'guest-base' and 'rootfs/usr/bin/Xorg' in members:
            raise RuntimeError('unexpected Xorg in guest component')
        if role == 'host-runtime':
            for name in ('host-tools/storage', 'host-tools/home/rocknix-default'):
                if name not in members or not members[name].isdir():
                    raise RuntimeError('missing real host sandbox directory: ' + name)

def compress(role, key, raw, store):
    managed, unpacked = {}, 0
    with tarfile.open(raw) as archive:
        for item in archive:
            if item.isfile():
                unpacked += item.size
            if role == 'guest-base':
                continue
            name = item.name.removeprefix('rootfs/')
            if item.name.startswith('rootfs/') and not item.isdir():
                if item.issym():
                    managed[name] = {'link': item.linkname}
                elif item.isfile():
                    managed[name] = {'sha256': hashlib.file_digest(archive.extractfile(item), 'sha256').hexdigest(), 'mode': item.mode}
                else:
                    raise RuntimeError('managed artifact contains a hardlink')
    compressed = raw.with_suffix('.tar.xz')
    with compressed.open('wb') as output:
        run(['xz', '-c', raw], stdout=output)
    sha = C['digest'](compressed)
    spec = {'format': 1, 'id': role, 'input_key': key, 'sha256': sha,
            'asset': sha + '.tar.xz', 'store_tag': 'components-v1-' + key[:3],
            'size': compressed.stat().st_size, 'unpacked_size': unpacked, 'managed': managed}
    C['descriptor'](spec, role, key)
    blob = store.directory / spec['asset']
    # Place complete files atomically in the destination filesystem, including
    # when --store is on a different mount from the build scratch directory.
    def bind(source, destination):
        fd, name = tempfile.mkstemp(prefix='.component-', dir=store.directory)
        os.close(fd)
        staged = Path(name)
        try:
            shutil.copyfile(source, staged)
            try:
                os.link(staged, destination)
            except FileExistsError:
                if C['digest'](destination) != C['digest'](staged):
                    raise RuntimeError('immutable cache binding collision: ' + destination.name)
        finally:
            staged.unlink(missing_ok=True)
    bind(compressed, blob)
    binding = store.directory / f'{role}-{key}.json'
    staged = raw.parent / 'descriptor.json'
    staged.write_bytes(C['encoded'](spec))
    bind(staged, binding)
    return spec


def prepare_trash(work):
    override = os.environ.get('ROCKNIX_TRASH_PACKAGES_DIR')
    if override:
        directory = Path(override).resolve()
    else:
        raw = docker_export('trash-packages', work)
        directory = work / 'trash'; directory.mkdir()
        with tarfile.open(raw) as archive:
            archive.extractall(directory, filter='data')
    audit_trash(directory)
    return directory


def audit_trash(directory):
    auditor = os.environ.get('ROCKNIX_PACKAGE_AUDITOR_IMAGE')
    if auditor:
        if not re.fullmatch('sha256:[0-9a-f]{64}', auditor):
            raise RuntimeError('use an immutable local package audit image')
        run(['docker', 'run', '--rm', '--network=none', '--platform', 'linux/arm64',
             '--mount', f'type=bind,src={directory},dst=/packages,readonly',
             '--mount', f'type=bind,src={PROJECT / "build-support/trash"},dst=/audit,readonly',
             auditor, '/usr/bin/python3', '/audit/check-packages.py', '/packages'])
    else:
        run([sys.executable, PROJECT / 'build-support/trash/check-packages.py', directory])



def cached_trash(store, spec, work):
    payload = work / 'packages.tar'
    with tarfile.open(store.blob(spec), 'r:xz') as archive:
        members = archive.getmembers()
        if (len(members) != 1 or members[0].name != 'payload/guest/trash-packages.tar' or
                not members[0].isfile() or members[0].size > 256 * 1024**2):
            raise RuntimeError('invalid cached package transaction')
        with payload.open('wb') as stream:
            shutil.copyfileobj(archive.extractfile(members[0]), stream)
    directory = work / 'packages'; directory.mkdir()
    unpacker = runpy.run_path(str(PROJECT / 'payload/guest/update-trash-packages.py'))
    unpacker['unpack'](payload, directory)
    audit_trash(directory)
    return directory


def build(store, output, plan_only=False):
    started = time.monotonic()
    keys, inputs = input_keys()
    specs = {role: store.find(role, keys[role]) for role in C['ROLES']}
    missing = [role for role, spec in specs.items() if spec is None]
    docker = any(role in DOCKER for role in missing)
    output.mkdir(parents=True, exist_ok=True)
    plan = {'format': 1, 'missing': missing, 'reused': [r for r in C['ROLES'] if r not in missing],
            'needs_docker': docker, 'input_keys': keys}
    (output / 'plan.json').write_bytes(C['encoded'](plan))
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
            stream.write(f'needs_docker={str(docker).lower()}\n')
    print(json.dumps(plan, indent=2), flush=True)
    if plan_only:
        return plan
    metrics = {'built': [], 'reused': plan['reused'], 'components': {}}
    with tempfile.TemporaryDirectory(prefix='component-build-', dir=output) as scratch:
        scratch = Path(scratch)
        trash = None
        for role in ('trash-packages', *[r for r in C['ROLES'] if r != 'trash-packages']):
            if specs[role] is not None:
                continue
            begin = time.monotonic(); work = scratch / role; work.mkdir()
            if role in ('trash-packages', 'guest-base') and trash is None:
                trash_work = scratch / 'trash-inputs'; trash_work.mkdir()
                if role == 'guest-base' and specs['trash-packages'] is not None:
                    trash = cached_trash(store, specs['trash-packages'], trash_work)
                else:
                    trash = prepare_trash(trash_work)
            raw = docker_export(role, work, trash if role == 'guest-base' else None) if role in DOCKER and role != 'trash-packages' else None
            payload = payload_tar(role, work, raw, trash)
            check_payload(role, payload)
            specs[role] = compress(role, keys[role], payload, store)
            metrics['built'].append(role)
            metrics['components'][role] = {'seconds': round(time.monotonic() - begin, 3), 'bytes': specs[role]['size']}
    if input_keys()[0] != keys:
        raise RuntimeError('source inputs changed during the build; rerun from a stable checkout')
    revision = run(['git', '-C', PROJECT, 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    value = {'format': 2, 'minimum_installer': 2, 'platform': 'linux/arm64', 'runtime_abi': C['ABI'],
             'commit': revision, 'built_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
             'local_override': bool(os.environ.get('ROCKNIX_TRASH_PACKAGES_DIR')),
             'dependency_lock': json.loads((PROJECT / 'build-support/components/dependencies.json').read_text()),
             'components': specs}
    C['release'](value)
    (output / 'release.json').write_bytes(C['encoded'](value))
    metrics['seconds'] = round(time.monotonic() - started, 3)
    (output / 'timings.json').write_bytes(C['encoded'](metrics))
    print(json.dumps(metrics, indent=2))
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store', type=Path, default=PROJECT / 'build/component-store')
    parser.add_argument('--repository', help='resolve previously published immutable components before building')
    parser.add_argument('--output', type=Path, default=PROJECT / 'dist/components')
    parser.add_argument('--plan', action='store_true')
    args = parser.parse_args()
    build(Store(args.store, args.repository), args.output, args.plan)


if __name__ == '__main__':
    main()
