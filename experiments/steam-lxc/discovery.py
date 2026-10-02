#!/usr/bin/env python3
"""Offline snapshot planner. Emits review data, never mount commands or writes."""
import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat


class Invalid(ValueError):
    pass


def absolute(value):
    if not value.startswith('/') or value.startswith('//') or any(
            ord(c) < 32 for c in value) or '..' in PurePosixPath(value).parts:
        raise Invalid(f'noncanonical absolute path: {value!r}')
    return str(PurePosixPath(value))


class Snapshot:
    def __init__(self, root):
        self.root = Path(root).resolve(strict=True)
        if self.root == Path('/'):
            raise Invalid('use an offline snapshot, never the live host root')

    def resolve(self, value):
        """Resolve absolute links relative to snapshot /, never host /."""
        pending = list(PurePosixPath(absolute(value)).parts[1:])
        parts, hops = [], 0
        while pending:
            part = pending.pop(0)
            if part in ('', '.'):
                continue
            if part == '..':
                if not parts:
                    raise Invalid('symlink traverses above snapshot root')
                parts.pop()
                continue
            candidate = self.root.joinpath(*parts, part)
            info = candidate.lstat()
            if stat.S_ISLNK(info.st_mode):
                hops += 1
                if hops > 40:
                    raise Invalid('symlink cycle or excessive link depth')
                target = os.readlink(candidate)
                if target.startswith('/'):
                    parts = []
                pending = list(PurePosixPath(target).parts) + pending
                if pending and pending[0] == '/':
                    pending.pop(0)
            else:
                parts.append(part)
        return '/' + '/'.join(parts)

    def local(self, value):
        return self.root / self.resolve(value).lstrip('/')


def vdf(text):
    """Deliberately strict quoted KeyValues subset; unknown syntax is an error."""
    tokens, pos = [], 0
    pattern = re.compile(r'\s+|//[^\n]*|[{}]|"(?:[^"\\]|\\["\\])*"')
    while pos < len(text):
        match = pattern.match(text, pos)
        if match is None:
            raise Invalid(f'unsupported VDF syntax at {pos}')
        token = match.group()
        pos = match.end()
        if token.isspace() or token.startswith('//'):
            continue
        tokens.append(token)
    index = 0

    def string(token):
        if not token.startswith('"'):
            raise Invalid('expected quoted VDF string')
        return re.sub(r'\\(["\\])', r'\1', token[1:-1])

    def obj(nested=False, depth=0):
        nonlocal index
        if depth > 32:
            raise Invalid('VDF nesting limit')
        result = {}
        while index < len(tokens):
            if tokens[index] == '}':
                if not nested:
                    raise Invalid('unexpected closing brace')
                index += 1
                return result
            key = string(tokens[index])
            index += 1
            if key in result or index >= len(tokens):
                raise Invalid('duplicate key or missing VDF value')
            value = tokens[index]
            index += 1
            result[key] = obj(True, depth + 1) if value == '{' else string(value)
        if nested:
            raise Invalid('unclosed VDF object')
        return result
    return obj()


def libraries(text):
    tree = vdf(text).get('libraryfolders')
    if not isinstance(tree, dict):
        raise Invalid('missing libraryfolders object')
    paths = []
    for key, value in tree.items():
        if key.isdigit():
            path = value.get('path') if isinstance(value, dict) else value
            if not isinstance(path, str):
                raise Invalid('library entry missing path')
            paths.append(absolute(path))
    return paths


def plan(snapshot, approved):
    """Explicit exact roots are analyst input, not inferred mount authority."""
    roots = {absolute(p) for p in approved}
    # Never accept administrative directories or broad storage/home roots.
    if any(not p.startswith(('/storage/', '/media/', '/run/media/')) or
           p in ('/storage/.local', '/storage/.local/share', '/storage/.config',
                 '/storage/rocknix-desktop', '/storage/scripts', '/storage/roms',
                 '/storage/games-internal', '/storage/games-external')
           for p in roots):
        raise Invalid('approval must name narrow data roots')
    report = {'status': 'review-only', 'mount_candidates': [], 'aliases': [],
              'links': [], 'blockers': [], 'absent': []}
    candidates = {}
    for alias in ('/storage/Steam', '/storage/.local/share/Steam'):
        try:
            target = snapshot.resolve(alias)
            if not snapshot.local(target).is_dir():
                raise Invalid('client root is not a directory')
            candidates[alias] = target
        except FileNotFoundError:
            report['absent'].append(alias)
        except (Invalid, OSError) as error:
            report['blockers'].append(f'{alias}: {error}')
    if len(set(candidates.values())) > 1:
        report['blockers'].append('ambiguous Steam installations; select explicitly')
        return report
    if not candidates:
        report['blockers'].append('no Steam installation found')
        return report
    client = next(iter(candidates.values()))
    paths = list(candidates) + [client, '/storage/.steam']
    try:
        paths += libraries(snapshot.local(client + '/steamapps/libraryfolders.vdf').read_text())
    except (Invalid, OSError) as error:
        report['blockers'].append(f'library discovery incomplete: {error}')
    seen = set()
    for path in dict.fromkeys(paths):
        try:
            target = snapshot.resolve(path)
            local = snapshot.local(target)
            if not local.is_dir():
                raise Invalid('data root is not a directory')
            if target not in roots:
                raise Invalid(f'exact resolved root needs review: {target}')
            if path != target:
                report['aliases'].append({'path': path, 'target': target})
            if target in seen:
                continue
            seen.add(target)
            info = local.stat()
            report['mount_candidates'].append({'source': target, 'destination': target,
                'mode': 'rw,nosuid,nodev', 'snapshot_uid': info.st_uid,
                'snapshot_gid': info.st_gid, 'idmap': 'requires native metadata inventory'})
            for directory, dirs, files in os.walk(local, followlinks=False):
                for name in dirs + files:
                    entry = Path(directory) / name
                    if entry.is_symlink():
                        logical = '/' + str(entry.relative_to(snapshot.root))
                        resolved = snapshot.resolve(logical)
                        report['links'].append({'path': logical, 'target': resolved})
                        if not any(resolved == root or resolved.startswith(root + '/') for root in roots):
                            report['blockers'].append(f'link target outside reviewed roots: {logical} -> {resolved}')
        except (Invalid, OSError) as error:
            report['blockers'].append(f'{path}: {error}')
    report['client'] = client
    try:
        report['arm64_client_present'] = snapshot.local(client + '/steamrtarm64/steam').is_file()
    except (OSError, Invalid):
        report['arm64_client_present'] = False
    report['limitations'] = ['No live mount, ABI, ownership or launch qualification',
        'Snapshot metadata may differ from device; contents and symlinks can race on a live tree',
        'Library VDF is untrusted; candidates must never feed privileged mount code directly',
        'Home saves outside Steam and runtime/provider dependencies need separate inventory']
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', required=True)
    parser.add_argument('--approve-root', action='append', default=[])
    args = parser.parse_args()
    print(json.dumps(plan(Snapshot(args.snapshot), args.approve_root), indent=2))
