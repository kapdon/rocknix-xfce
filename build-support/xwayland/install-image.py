#!/usr/bin/python3
"""Install only the offline X11 payload, preserving newer installed packages."""
from pathlib import Path
import runpy
import subprocess
import sys


def main():
    directory = Path(sys.argv[1]).resolve()
    candidates = runpy.run_path(str(directory / 'check-packages.py'))['packages'](directory)
    selected = {}
    for name, (path, wanted) in candidates.items():
        current = subprocess.run(['dpkg-query', '-W', '-f=${db:Status-Status} ${Version}', name],
                                 capture_output=True, text=True)
        status, _, version = current.stdout.partition(' ')
        if status == 'installed' and subprocess.run(
                ['dpkg', '--compare-versions', version, 'ge', wanted]).returncode == 0:
            continue
        selected[name] = str(path)
    if not selected:
        return
    base = ['apt-get', '--no-remove', '--no-install-recommends', 'install', *selected.values()]
    plan = subprocess.check_output([base[0], '--simulate', *base[1:]], text=True)
    for line in plan.splitlines():
        if line.startswith(('Remv ', 'Purg ')):
            raise RuntimeError('X11 update would remove packages')
        if line.startswith(('Inst ', 'Conf ')) and line.split()[1].split(':')[0] not in selected:
            raise RuntimeError('X11 update would change unrelated packages')
    automatic = set(subprocess.check_output(['apt-mark', 'showauto'], text=True).splitlines()) & selected.keys()
    try:
        subprocess.run([base[0], '-y', *base[1:]], check=True)
    finally:
        if automatic:
            subprocess.run(['apt-mark', 'auto', *sorted(automatic)], check=True)
    if subprocess.check_output(['dpkg', '--audit'], text=True).strip():
        raise RuntimeError('package database audit failed')


if __name__ == '__main__':
    main()
