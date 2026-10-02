#!/usr/bin/python3
"""Build a flat guest-only package payload from native build artifacts."""
from pathlib import Path
import sys
import tarfile


def build(directory, output, tools=None):
    artifacts = sorted(path for path in directory.iterdir() if path.name.endswith(
        ('.deb', '.dsc', '.tar.xz', '.tar.gz', '.changes', '.buildinfo')))
    if not any(path.suffix == '.deb' for path in artifacts):
        raise RuntimeError('native package artifacts missing')
    tools = tools or Path(__file__).resolve().parents[1] / 'build-support/trash'
    artifacts += [tools / name for name in ('check-packages.py', 'install-image.py')]
    if any(path.is_symlink() or not path.is_file() for path in artifacts):
        raise RuntimeError('package inputs must be regular files')
    if len({path.name for path in artifacts}) != len(artifacts):
        raise RuntimeError('duplicate package artifact name')
    with tarfile.open(output, 'w', dereference=False) as archive:
        for path in artifacts:
            archive.inodes.clear()
            info = archive.gettarinfo(str(path), arcname=path.name)
            info.uid = info.gid = 0
            info.uname = info.gname = ''
            info.mode = 0o644
            with path.open('rb') as stream:
                archive.addfile(info, stream)


if __name__ == '__main__':
    build(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]) if len(sys.argv) > 3 else None)
