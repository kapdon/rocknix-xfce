#!/usr/bin/env python3
"""Guest package payload and retained-security guards, without installing."""
import io
from pathlib import Path
import runpy
import sys
import tarfile
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

repo = Path(__file__).resolve().parents[1]
unpack = runpy.run_path(str(repo / 'payload/guest/update-trash-packages.py'))['unpack']
pack = runpy.run_path(str(repo / 'scripts/package-trash.py'))['build']
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    inputs = root / 'inputs'; inputs.mkdir()
    (inputs / 'fixture.deb').write_bytes(b'fixture')
    archive = root / 'packages.tar'
    pack(inputs, archive)
    destination = root / 'valid'; destination.mkdir()
    unpack(archive, destination)
    assert (destination / 'fixture.deb').read_bytes() == b'fixture'
    for index, (name, kind) in enumerate((('../escape.deb', tarfile.REGTYPE),
                                        ('link.deb', tarfile.SYMTYPE),
                                        ('dir.deb', tarfile.DIRTYPE),
                                        ('command.sh', tarfile.REGTYPE),
                                        ('fixture.deb', tarfile.REGTYPE))):
        bad = root / f'bad{index}.tar'
        with tarfile.open(bad, 'w') as output:
            for normal in ('check-packages.py', 'install-image.py', 'fixture.deb'):
                member = tarfile.TarInfo(normal); member.size = 1
                output.addfile(member, io.BytesIO(b'x'))
            member = tarfile.TarInfo(name); member.type = kind; member.linkname = '/etc/shadow'
            output.addfile(member)
        out = root / f'out{index}'; out.mkdir()
        try:
            unpack(bad, out)
        except RuntimeError:
            assert not list(out.iterdir()), 'validate all members before writes'
        else:
            raise AssertionError('unsafe package payload accepted')

api = runpy.run_path(str(repo / 'build-support/trash/install-image.py'))
assert api['validate_plan']('Inst libglib2.0-dev (candidate)', {'libglib2.0-dev'}) == {'libglib2.0-dev'}
assert api['validate_plan']('Conf libglib2.0-dev (candidate)', {'libglib2.0-dev'}) == set()
try:
    api['validate_plan']('Inst gvfs (candidate)\nConf user-package (1.0)')
except RuntimeError as error:
    assert 'unrelated package: user-package' in str(error)
else:
    raise AssertionError('unrelated interrupted package configuration accepted')
main = api['main']; calls = []
def fake_run(command, **kwargs):
    calls.append(command)
    assert command[0] != 'apt-get', 'newer security packages must never invoke APT'
    if command[0] == 'dpkg-query':
        return SimpleNamespace(returncode=0, stdout='999.0')
    assert command[:2] == ['dpkg', '--compare-versions']
    return SimpleNamespace(returncode=0)
def fake_output(command, **kwargs):
    assert command[0] == 'dpkg-deb'
    return '2.84.4-3~deb13u5+rocknix1\n'
with tempfile.TemporaryDirectory() as temporary:
    with patch.dict(main.__globals__, runtime_paths=lambda _: ['/fixture.deb'] * len(api['PACKAGES'])), \
         patch.object(api['subprocess'], 'run', side_effect=fake_run), \
         patch.object(api['subprocess'], 'check_output', side_effect=fake_output):
        with patch.object(sys, 'argv', ['install-image.py', temporary, '--retained']):
            main()
        with patch.object(sys, 'argv', ['install-image.py', temporary]):
            try:
                main()
            except RuntimeError as error:
                assert 'newer than the candidate' in str(error)
            else:
                raise AssertionError('fresh image downgrade accepted')
print('PASS: flat package payload, pre-write rejection, optional-family plans and retained security no-downgrade')
