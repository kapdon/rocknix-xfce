#!/usr/bin/python3
"""Publish a tested component manifest as an immutable versioned release."""
import argparse
import json
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import tempfile

PROJECT = Path(__file__).resolve().parents[1]
P = runpy.run_path(str(PROJECT / 'scripts/publish-components.py'))
C = P['C']


def publish(tag, manifest, store, repository):
    if not re.fullmatch(r'v\d+\.\d+\.\d+(?:-(?:alpha|beta|rc)\.\d+)?', tag):
        raise RuntimeError('invalid version tag')
    def output(*args):
        return subprocess.check_output(args, text=True).strip()
    revision = output('git', '-C', str(PROJECT), 'rev-parse', 'HEAD')
    remote = output('git', '-C', str(PROJECT), 'ls-remote', '--heads', 'origin', 'refs/heads/dev')
    if remote.split() != [revision, 'refs/heads/dev']:
        raise RuntimeError('release source must match remote dev')
    if output('git', '-C', str(PROJECT), 'ls-remote', '--tags', 'origin', 'refs/tags/' + tag):
        raise RuntimeError('version tag already exists')
    # This validates clean/exact source and publishes immutable dependencies.
    # It never advances the development pointer or tag.
    P['publish'](manifest, store, repository, components_only=True)
    value = C['release'](json.loads(manifest.read_text()))
    sha = C['digest'](manifest)
    def gh(*args):
        subprocess.run(['gh', *map(str, args), '--repo', repository], check=True)
    with tempfile.TemporaryDirectory(prefix='versioned-components-') as scratch:
        scratch = Path(scratch)
        name = f'rocknix-desktop-components-{revision}-{sha}.json'
        candidate = scratch / name; shutil.copyfile(manifest, candidate)
        helper_source = PROJECT / 'payload/bin/rocknix-components'
        helper_sha = C['digest'](helper_source)
        helper = scratch / f'rocknix-components-{helper_sha}.py'
        shutil.copyfile(helper_source, helper)
        notes = scratch / 'notes.md'
        notes.write_text(f'Commit: `{revision}`\nBuilt: {value["built_at"]}\n\n'
                         f'ROCKNIX Desktop component release. Install with `--release {tag}`.\n')
        prerelease = '-' in tag
        flags = ['--prerelease'] if prerelease else []
        gh('release', 'create', tag, candidate, helper, '--target', revision,
           '--draft', *flags, '--title', 'ROCKNIX Desktop ' + tag, '--notes-file', notes)
        released = output('gh', 'release', 'view', tag, '--repo', repository, '--json', 'assets',
                          '--jq', f'.assets[] | select(.name == "{name}") | .updatedAt')
        if not released:
            raise RuntimeError('manifest upload was not confirmed')
        pointer = {'format': 2, 'commit': revision, 'asset': name, 'sha256': sha,
                   'size': candidate.stat().st_size, 'built_at': value['built_at'],
                   'released_at': released, 'version': tag,
                   'channel': 'prerelease' if prerelease else 'stable',
                   'bootstrap': {'asset': helper.name, 'sha256': helper_sha, 'size': helper.stat().st_size}}
        latest = scratch / 'latest.json'; latest.write_bytes(C['encoded'](pointer))
        gh('release', 'upload', tag, latest)
        gh('release', 'edit', tag, '--draft=false', '--latest=' + ('false' if prerelease else 'true'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tag')
    parser.add_argument('--manifest', type=Path, default=PROJECT / 'dist/components/release.json')
    parser.add_argument('--store', type=Path, default=PROJECT / 'build/component-store')
    parser.add_argument('--repository', default='kapdon/rocknix-desktop')
    args = parser.parse_args()
    publish(args.tag, args.manifest, args.store, args.repository)
