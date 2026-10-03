#!/usr/bin/env python3
"""Home persistence around a replacement update: setup, verify, cleanup.

Run with Desktop active on the reserved RP6. Fixtures are created as mapped
container root; the host records hashes/metadata without exposing user data.
"""
import argparse
import json
from pathlib import Path
import runpy

GUEST = r'''
import hashlib,json,os,stat
from pathlib import Path
assert os.getuid()==0
assert Path('/proc/self/uid_map').read_text().split()==['0','200000','65536']
base=Path('/home/rocknix/.rocknix-update-ownership-probe')
system=Path('/var/tmp/rocknix-update-system-probe')
def inventory():
    result={}
    for p in [base,*sorted(base.iterdir())]:
        s=p.lstat()
        result[p.name]={'inode':s.st_ino,'owner':[s.st_uid,s.st_gid],
            'mode':s.st_mode,'links':s.st_nlink,
            'content':hashlib.sha256(p.read_bytes()).hexdigest() if stat.S_ISREG(s.st_mode)
                      else os.readlink(p) if p.is_symlink() else None,
            'xattrs':{key:os.getxattr(p,key,follow_symlinks=False).hex()
                      for key in os.listxattr(p,follow_symlinks=False)}}
    return result
if phase=='setup':
    assert not os.path.lexists(base) and not os.path.lexists(system)
    base.mkdir(mode=0o700)
    for name,uid in [('root',0),('user',1000),('service',2056)]:
        p=base/name;p.write_bytes(b'ROCKNIX replacement update fixture\n')
        p.chmod(0o640);os.chown(p,uid,uid)
    os.setxattr(base/'user','user.rocknix-test',b'preserve')
    os.link(base/'user',base/'hardlink')
    (base/'symlink').symlink_to('user')
    system.write_text('old system only\n')
    print(json.dumps(inventory()))
else:
    assert not system.exists(),'old system was retained'
    assert inventory()==expected,'home inode/owner/mode/content/link/xattr changed'
    if phase=='cleanup':
        for p in base.iterdir(): p.unlink()
        base.rmdir()
    print('PASS: home inodes, mixed owners, modes, hardlinks, symlinks and xattrs preserved')
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['setup', 'verify', 'cleanup'])
    args = parser.parse_args()
    host = Path('/storage/rocknix-desktop/managed/host')
    root = Path('/storage/rocknix-desktop/data/rootfs')
    record = host / 'state/update-preservation-test.json'
    expected = {}
    if args.phase != 'setup':
        data = json.loads(record.read_text())
        assert [root.stat().st_dev, root.stat().st_ino] != data['rootfs'], 'rootfs was not replaced'
        expected = data['home']
    else:
        assert not record.exists() and not record.is_symlink()
    runtime = runpy.run_path(str(host / 'bin/rocknix-lxc'))['Runtime'](host / 'host-tools', root)
    result = runtime.attach('/usr/bin/python3', '-',
        input='phase='+repr(args.phase)+'\nexpected='+repr(expected)+'\n'+GUEST)
    assert result.returncode == 0, result.stdout + result.stderr
    if args.phase == 'setup':
        with record.open('x') as stream:
            json.dump({'rootfs':[root.stat().st_dev,root.stat().st_ino],
                       'home':json.loads(result.stdout)},stream)
        record.chmod(0o600)
        print('PASS: mapped mixed-owner home fixtures created')
    else:
        print(result.stdout)
        if args.phase == 'cleanup': record.unlink()


if __name__ == '__main__':
    main()
