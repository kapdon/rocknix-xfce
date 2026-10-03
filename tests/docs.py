#!/usr/bin/python3
"""Validate checked-in documentation links and installation instructions."""
from pathlib import Path
import re
import subprocess

paths = [Path(p) for p in subprocess.check_output(
    ['git', 'ls-files', '--cached', '--others', '--exclude-standard', '*.md'],
    text=True).splitlines()]
for path in paths:
    text = path.read_text()
    for target in re.findall(r'\]\(([^)]+)\)', text):
        if '://' in target or target.startswith('#'):
            continue
        target = target.split('#', 1)[0]
        assert (path.parent / target).exists(), (path, target)

readme = Path('README.md').read_text()
assert 'navigation and the full terminal layout' not in readme
assert 'does not replace the native ROCKNIX keyboard' in readme
assert 'dist/components/release.json' in Path('docs/build.md').read_text()
print('PASS: all checked-in documentation links, Desktop-only keyboard and checksum instructions')
