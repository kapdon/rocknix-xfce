#!/usr/bin/env python3
"""Cumulative release notes and conflict-safe successful-build records."""
import base64
from pathlib import Path
import runpy
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
N = runpy.run_path(str(PROJECT / 'scripts/development-release-notes.py'))
R = runpy.run_path(str(PROJECT / 'scripts/record-development-changelog.py'))
REVISION = 'a' * 40
BUILT = '2026-10-02T12:00:00Z'


def rejects(fn, *args):
    try:
        fn(*args)
    except RuntimeError:
        return
    raise AssertionError('unsafe changelog operation accepted')


def commit(subject, author=None):
    return {'sha': 'b' * 40, 'html_url': 'https://github.com/owner/repo/commit/' + 'b' * 40,
            'commit': {'message': subject}, 'author': author}


calls = []
def api(endpoint, paginate=False, repository=None):
    calls.append((endpoint, paginate, repository))
    if endpoint == 'releases/latest':
        return {'tag_name': 'v0.1.0'}
    return [{'total_commits': 4, 'commits': [commit('fix: Apps *and* [Settings]'),
             commit(N['RECORD_SUBJECT'], {'login': 'github-actions[bot]'})]},
            {'total_commits': 4, 'commits': [commit('fix: retain caches'),
             commit(N['RECORD_SUBJECT'])]}]


with patch.dict(N['notes'].__globals__, api=api):
    notes = N['notes'](REVISION, BUILT, 'owner/repo')
assert calls == [('releases/latest', False, 'owner/repo'),
                 (f'compare/v0.1.0...{REVISION}?per_page=100', True, 'owner/repo')]
assert r'fix: Apps \*and\* \[Settings\]' in notes
assert 'fix: retain caches' in notes
assert notes.count('record development changelog') == 1  # Never hide a human commit.
assert f'https://github.com/owner/repo/compare/v0.1.0...{REVISION}' in notes
with patch.dict(N['notes'].__globals__, api=lambda endpoint, **kwargs: (
        {'tag_name': 'v0.1.0'} if endpoint == 'releases/latest' else [{'total_commits': 2, 'commits': []}])):
    rejects(N['notes'], REVISION, BUILT)
print('PASS: paginated changes since latest stable, Markdown escaping, bot-only filtering and completeness')

original = (PROJECT / 'CHANGELOG.md').read_text()
snapshot = N['render_changelog'](original, notes)
before, section, after = N['changelog_section'](snapshot)
assert section == '\n\n## Development\n\n' + notes.rstrip() + '\n\n'
assert (before, after) == (N['changelog_section'](original)[0], N['changelog_section'](original)[2])
assert 'v0.1.0' in after
for invalid in ['missing markers', original + N['CHANGELOG_START'],
                N['CHANGELOG_END'] + N['CHANGELOG_START']]:
    rejects(N['render_changelog'], invalid, notes)
print('PASS: release notes copied exactly and stable changelog history retained')

current = original
requests = []
def remote_api(repository, endpoint, body=None):
    assert repository == 'owner/repo'
    requests.append((endpoint, body))
    if body is None:
        return {'encoding': 'base64', 'sha': 'c' * 40,
                'content': base64.b64encode(current.encode()).decode()}
    return {'commit': {'sha': 'd' * 40}}


with patch.dict(R['record'].__globals__, api=remote_api):
    R['record']('owner/repo', REVISION, snapshot, original)
    assert len(requests) == 2
    endpoint, body = requests[-1]
    assert endpoint == 'contents/CHANGELOG.md'
    assert body['sha'] == 'c' * 40 and body['branch'] == 'dev'
    assert body['message'] == N['RECORD_SUBJECT']
    assert base64.b64decode(body['content']).decode() == snapshot
    requests.clear(); current = snapshot
    R['record']('owner/repo', REVISION, snapshot, original)
    assert len(requests) == 1  # Idempotent after an acknowledged or uncertain PUT.
    requests.clear(); current = original + '\nConcurrent human edit.\n'
    rejects(R['record'], 'owner/repo', REVISION, snapshot, original)
    assert len(requests) == 1 and requests[0][1] is None
    for invalid in [snapshot.replace(REVISION, 'e' * 40), snapshot + '\nChanged stable history.\n']:
        requests.clear()
        rejects(R['record'], 'owner/repo', REVISION, invalid, original)
        assert not requests
print('PASS: exact published revision, idempotent writes and concurrent edit protection')
