#!/usr/bin/env python3
"""Record the published build's changelog on dev without changing its source checkout."""
import argparse
import base64
import json
from pathlib import Path
import re
import runpy
import subprocess

PROJECT = Path(__file__).resolve().parents[1]
N = runpy.run_path(str(PROJECT / 'scripts/development-release-notes.py'))


def api(repository, endpoint, body=None):
    command = ['gh', 'api', f'repos/{repository}/{endpoint}']
    if body is not None:
        command += ['--method', 'PUT', '--input', '-']
    result = subprocess.run(command, input=None if body is None else json.dumps(body),
                            capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def record(repository, revision, snapshot, original):
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise RuntimeError('revision must be a full commit SHA')
    before, section, after = N['changelog_section'](snapshot)
    old_before, _, old_after = N['changelog_section'](original)
    if (before, after) != (old_before, old_after) or f'Commit: `{revision}`\n' not in section:
        raise RuntimeError('changelog does not match the published revision or checked-in history')
    current = api(repository, 'contents/CHANGELOG.md?ref=dev')
    if current.get('encoding') != 'base64':
        raise RuntimeError('unsupported GitHub changelog encoding')
    content = base64.b64decode(current['content']).decode()
    if content == snapshot:
        print('Published changelog already recorded.')
        return
    if content != original:
        raise RuntimeError('CHANGELOG.md changed on dev during this build; refusing to overwrite it')
    # The Contents API preserves unrelated concurrent commits, and the expected
    # blob SHA rejects a concurrent edit of this file. Never force-push dev.
    result = api(repository, 'contents/CHANGELOG.md', {
        'branch': 'dev', 'sha': current['sha'], 'message': N['RECORD_SUBJECT'],
        'content': base64.b64encode(snapshot.encode()).decode(),
    })
    print('Recorded development changelog: ' + result['commit']['sha'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', default=N['REPO'])
    parser.add_argument('--revision', required=True)
    parser.add_argument('--changelog', type=Path, default=PROJECT / 'dist/components/CHANGELOG.md')
    args = parser.parse_args()
    revision = subprocess.check_output(['git', '-C', PROJECT, 'rev-parse', 'HEAD'], text=True).strip()
    if revision != args.revision:
        parser.error('checkout must match the published revision')
    record(args.repository, revision, args.changelog.read_text(), (PROJECT / 'CHANGELOG.md').read_text())
