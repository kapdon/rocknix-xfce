#!/usr/bin/python3
"""Publish immutable components first, then advance the rolling release pointer."""
import argparse
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import tempfile

PROJECT = Path(__file__).resolve().parents[1]
B = runpy.run_path(str(PROJECT / 'scripts/build-components.py'))
C = B['C']


class Publisher:
    def __init__(self, repository, revision):
        self.repository, self.revision = repository, revision
        self.known = {}

    def gh(self, *args, **kwargs):
        return subprocess.run(['gh', *map(str, args)], check=True, **kwargs)

    def assets(self, tag):
        if tag not in self.known:
            result = subprocess.run(['gh', 'api', f'repos/{self.repository}/releases/tags/{tag}'],
                                    capture_output=True, text=True)
            if result.returncode:
                if '(HTTP 404)' not in result.stderr:
                    raise RuntimeError('cannot inspect release: ' + result.stderr)
                self.gh('release', 'create', tag, '--repo', self.repository, '--target', self.revision,
                        '--prerelease', '--latest=false', '--title', tag,
                        '--notes', 'Immutable Desktop component artifacts. Referenced by release manifests; do not delete.')
                self.known[tag] = {}
            else:
                self.known[tag] = {item['name']: item for item in json.loads(result.stdout)['assets']}
        return self.known[tag]

    def upload(self, tag, name, digest, size, source=None):
        assets = self.assets(tag)
        if name in assets:
            item = assets[name]
            if item['state'] != 'uploaded' or item['size'] != size or item.get('digest') != 'sha256:' + digest:
                raise RuntimeError('immutable asset collision or incomplete upload: ' + name)
            return False
        if len(assets) >= 990:
            raise RuntimeError('component shard is full; add a new store layout before publishing')
        if source is None or not source.is_file() or C['digest'](source) != digest or source.stat().st_size != size:
            raise RuntimeError('missing verified local artifact: ' + name)
        if source.name != name:
            raise RuntimeError('asset filename mismatch')
        self.gh('release', 'upload', tag, source, '--repo', self.repository)
        self.known.pop(tag)
        item = self.assets(tag).get(name)
        if not item or item.get('digest') != 'sha256:' + digest or item['size'] != size or item['state'] != 'uploaded':
            raise RuntimeError('uploaded artifact verification failed: ' + name)
        return True


def publish(manifest, store, repository, components_only=False):
    value = C['release'](json.loads(manifest.read_text()))
    revision = subprocess.check_output(['git', '-C', PROJECT, 'rev-parse', 'HEAD'], text=True).strip()
    if value['commit'] != revision or value.get('local_override') or subprocess.check_output(
            ['git', '-C', PROJECT, 'status', '--porcelain'], text=True).strip():
        raise RuntimeError('publication requires a clean exact commit and the locked native package build')
    keys, _ = B['input_keys']()
    if any(spec['input_key'] != keys[role] for role, spec in value['components'].items()):
        raise RuntimeError('build inputs changed after the component build')
    publisher = Publisher(repository, revision)
    with tempfile.TemporaryDirectory(prefix='component-publication-') as scratch:
        scratch = Path(scratch)
        # Generate release highlights and the full changelog before publication.
        # Record the latter on dev after the pointer, notes and tag all succeed.
        notes = manifest.parent / 'development-notes.md'
        if not components_only:
            with notes.open('w') as stream:
                subprocess.run(['python3', PROJECT / 'scripts/development-release-notes.py',
                                revision, value['built_at'], '--repository', repository,
                                '--changelog', manifest.parent / 'CHANGELOG.md'],
                               check=True, stdout=stream)
        # Failure anywhere in these immutable uploads leaves the old pointer.
        for role, spec in value['components'].items():
            publisher.upload(spec['store_tag'], spec['asset'], spec['sha256'], spec['size'],
                             store / spec['asset'])
            binding = scratch / f"{role}-{spec['input_key']}.json"
            binding.write_bytes(C['encoded'](spec))
            publisher.upload(spec['store_tag'], binding.name, C['digest'](binding), binding.stat().st_size, binding)
        if components_only:
            print('Component artifacts verified; development release unchanged.')
            return
        sha = C['digest'](manifest)
        name = f'rocknix-desktop-components-{revision}-{sha}.json'
        candidate = scratch / name; shutil.copyfile(manifest, candidate)
        publisher.upload('development', name, sha, candidate.stat().st_size, candidate)
        helper_source = PROJECT / 'payload/bin/rocknix-components'
        helper_sha = C['digest'](helper_source)
        helper = scratch / f'rocknix-components-{helper_sha}.py'; shutil.copyfile(helper_source, helper)
        publisher.upload('development', helper.name, helper_sha, helper.stat().st_size, helper)
        pointer = {'format': 2, 'commit': revision, 'asset': name, 'sha256': sha,
                   'size': candidate.stat().st_size, 'built_at': value['built_at'],
                   'released_at': publisher.assets('development')[name]['updated_at'],
                   'bootstrap': {'asset': helper.name, 'sha256': helper_sha, 'size': helper.stat().st_size}}
        latest = scratch / 'latest.json'; latest.write_bytes(C['encoded'](pointer))
        publisher.gh('release', 'upload', 'development', latest, '--clobber', '--repo', repository)
        publisher.gh('release', 'edit', 'development', '--repo', repository, '--prerelease', '--latest=false',
                     '--title', 'Rolling development build', '--notes-file', notes)
        # Retain immutable manifests and components; no rolling asset pruning.
        tag = publisher.gh('api', f'repos/{repository}/git/tags', '--method', 'POST',
                           '-f', 'tag=development', '-f', f'object={revision}', '-f', 'type=commit',
                           '-f', f'message=Rolling development components ({revision})', '--jq', '.sha',
                           capture_output=True, text=True).stdout.strip()
        publisher.gh('api', f'repos/{repository}/git/refs/tags/development', '--method', 'PATCH',
                     '-f', f'sha={tag}', '-F', 'force=true')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=PROJECT / 'dist/components/release.json')
    parser.add_argument('--store', type=Path, default=PROJECT / 'build/component-store')
    parser.add_argument('--repository', default='kapdon/rocknix-desktop')
    parser.add_argument('--components-only', action='store_true',
                        help='publish reusable artifacts without changing any channel pointer or tag')
    args = parser.parse_args()
    publish(args.manifest, args.store, args.repository, args.components_only)
