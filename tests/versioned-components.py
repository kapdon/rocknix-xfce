#!/usr/bin/python3
"""Versioned component publication stays draft until all installer assets exist."""
import json
from pathlib import Path
import runpy
import tempfile
from unittest.mock import patch

P = runpy.run_path('scripts/publish-versioned-components.py')
with tempfile.TemporaryDirectory() as temporary:
    work = Path(temporary)
    manifest = work / 'release.json'
    manifest.write_text(json.dumps({'built_at': '2026-10-03T00:00:00Z'}))
    calls = []
    pointer = None
    collision = False
    remote_mismatch = False
    fail_pointer = False
    def output(args, **kwargs):
        if 'rev-parse' in args:
            return 'a' * 40
        if '--heads' in args:
            return ('b' if remote_mismatch else 'a') * 40 + '\trefs/heads/dev'
        if '--tags' in args:
            return 'existing' if collision else ''
        assert args[:3] == ('gh', 'release', 'view')
        return '2026-10-03T01:00:00Z'
    def run(args, **kwargs):
        calls.append(args)
        if args[1:3] == ['release', 'upload']:
            data = json.loads(Path(args[4]).read_text())
            assert data['format'] == 2 and data['commit'] == 'a' * 40
            assert data['asset'].endswith('.json') and data['bootstrap']['asset'].endswith('.py')
            assert data['version'] in ('v0.2.0', 'v0.2.0-beta.1')
            if fail_pointer:
                raise RuntimeError('injected pointer upload failure')
    def dependencies(*args, **kwargs):
        assert kwargs == {'components_only': True}
        calls.append(['dependencies'])
    with patch.dict(P['P'], publish=dependencies), patch.dict(P['C'], release=lambda x: x), \
         patch('subprocess.check_output', side_effect=output), patch('subprocess.run', side_effect=run):
        for tag in ('v0.2.0', 'v0.2.0-beta.1'):
            calls.clear()
            P['publish'](tag, manifest, work, 'owner/repo')
            assert calls[0] == ['dependencies']
            create, upload, edit = calls[1:]
            assert '--draft' in create and create[1:3] == ['release', 'create']
            assert '--draft=false' in edit and edit[1:3] == ['release', 'edit']
            assert ('--prerelease' in create) == ('-' in tag)
            assert ('--latest=false' in edit) == ('-' in tag)
        for case in ('tag', 'remote', 'pointer', 'syntax'):
            calls.clear()
            collision, remote_mismatch, fail_pointer = case == 'tag', case == 'remote', case == 'pointer'
            try:
                P['publish']('bad' if case == 'syntax' else 'v0.2.0', manifest, work, 'owner/repo')
                raise AssertionError('publication guard failed')
            except RuntimeError:
                pass
            assert not any('--draft=false' in call for call in calls)
            if case != 'pointer':
                assert not calls
print('PASS: versioned component publication order, source/tag guards and pointer failure isolation')
