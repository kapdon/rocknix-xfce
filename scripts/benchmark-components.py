#!/usr/bin/python3
"""Measure warm component builds from real cached artifacts, without Docker.

Build once with scripts/build-components.py first. Run this script inside a
resource-limited Ubuntu container for runner-like packaging comparisons. This is
not an estimate of GitHub queue, setup, network or publication time.
"""
import argparse
import json
import platform
from pathlib import Path
import runpy
import shutil
import subprocess
import tempfile
import time
import uuid

PROJECT = Path(__file__).resolve().parents[1]
SOURCES = ('Dockerfile.rootfs', '.dockerignore', 'rootfs-overlay', 'build-support',
           'scripts', 'payload', 'README.md', 'install.sh', 'install-device.sh',
           'uninstall.sh', 'upgrade.sh')


def optional_text(path):
    source = Path(path)
    return source.read_text().strip() if source.is_file() else None


def measure(store_path, output, samples):
    builder = runpy.run_path(str(PROJECT / 'scripts/build-components.py'))
    store = builder['Store'](store_path)
    keys, _ = builder['input_keys']()
    missing = [role for role, key in keys.items() if store.find(role, key) is None]
    if missing:
        raise RuntimeError('finish the real component build first: ' + ', '.join(missing))
    output.mkdir(parents=True, exist_ok=True)
    report = {
        'commit': subprocess.check_output(['git', '-C', PROJECT, 'rev-parse', 'HEAD'], text=True).strip(),
        'python': platform.python_version(), 'architecture': platform.machine(),
        'xz': subprocess.check_output(['xz', '--version'], text=True).splitlines()[0],
        'os_release': optional_text('/etc/os-release'),
        'cpu_max': optional_text('/sys/fs/cgroup/cpu.max'),
        'cpuset': optional_text('/sys/fs/cgroup/cpuset.cpus.effective'),
        'memory_max': optional_text('/sys/fs/cgroup/memory.max'), 'runs': [],
    }
    original_run, calls = builder['run'], []
    with tempfile.TemporaryDirectory(prefix='component-benchmark-') as scratch:
        source = Path(scratch)
        for name in SOURCES:
            original = PROJECT / name
            if original.is_dir():
                shutil.copytree(original, source / name, symlinks=True,
                                ignore=shutil.ignore_patterns('__pycache__'))
            else:
                shutil.copy2(original, source / name)
        # Only the disposable source copy receives CSS edits. Read commit
        # metadata from its originating checkout; every producer remains real.
        def record(args, **kwargs):
            if str(args[0]) == 'docker':
                raise AssertionError('warm/config build unexpectedly invokes Docker')
            if str(args[0]) == 'git':
                assert args[1] == '-C' and Path(args[2]) == source
                args = [*args[:2], PROJECT, *args[3:]]
            if str(args[0]) == 'xz':
                calls.append({'program': 'xz', 'input_bytes': Path(args[-1]).stat().st_size})
            return original_run(args, **kwargs)
        state = builder['build'].__globals__
        state['PROJECT'], state['run'] = source, record
        css = source / 'rootfs-overlay/etc/xdg/waybar/style.css'
        original_css, nonce = css.read_bytes(), uuid.uuid4().hex
        try:
            for kind in ('warm', 'css'):
                for number in range(1, samples + 1):
                    case = f'{kind}-{number}'
                    calls.clear()
                    if kind == 'css':
                        css.write_bytes(original_css + f'\n/* component benchmark {nonce} {case} */\n'.encode())
                    started = time.monotonic()
                    builder['build'](store, output / case)
                    elapsed = time.monotonic() - started
                    metrics = json.loads((output / case / 'timings.json').read_text())
                    wanted = ['guest-integration'] if kind == 'css' else []
                    assert metrics['built'] == wanted, metrics
                    assert len(calls) == len(wanted), calls
                    report['runs'].append({'case': case, 'seconds': round(elapsed, 3),
                                           'built': metrics['built'], 'reused': metrics['reused'],
                                           'producer_calls': calls.copy(),
                                           'component_timings': metrics['components']})
        finally:
            (output / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store', type=Path, default=PROJECT / 'build/component-store')
    parser.add_argument('--output', type=Path, default=PROJECT / 'dist/component-benchmark')
    parser.add_argument('--samples', type=int, choices=range(1, 11), default=3)
    args = parser.parse_args()
    measure(args.store.resolve(), args.output.resolve(), args.samples)
