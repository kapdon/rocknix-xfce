#!/usr/bin/env python3
"""Exercise bootstrap package decisions without root, APT or a container."""
import os
from pathlib import Path
import subprocess
import tempfile

source = Path('payload/guest/bootstrap-container.sh').read_text()
function = source[source.index('prepare_packages() {'):source.index('[ "$#" -le 1 ]')]
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    query = root / 'dpkg-query'
    query.write_text('#!/bin/sh\n'
        'if [ "$3" = "$FAIL_PACKAGE" ]; then printf "%s" "$FAIL_STATUS"; exit "$FAIL_CODE"; fi\n'
        'printf "install ok installed"\n')
    query.chmod(0o755)
    apt = root / 'apt-get'
    apt.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >>"$APT_LOG"\n')
    apt.chmod(0o755)
    log = root / 'apt-log'
    env = dict(os.environ, PATH=str(root) + ':' + os.environ['PATH'], APT_LOG=str(log),
               FAIL_PACKAGE='', FAIL_STATUS='', FAIL_CODE='0')
    def run(mode='', **override):
        return subprocess.run(['bash', '-euc', function + '\nprepare_packages ' + mode],
                              env=dict(env, **override), capture_output=True, text=True)
    for mode in ('', '--retained'):
        assert run(mode).returncode == 0
        for status, code in (('install ok unpacked', '0'), ('', '1')):
            result = run(mode, FAIL_PACKAGE='python3-gi', FAIL_STATUS=status, FAIL_CODE=code)
            assert result.returncode != 0 and 'repair it with guest sudo/APT' in result.stderr
        assert not log.exists(), 'retained bootstrap invoked APT'
    assert run('--unknown').returncode != 0 and not log.exists()

updater = Path('payload/bin/rocknix-lxc-upgrade').read_text()
assert 'bootstrap-container.sh' not in updater  # Updates boot a newly assembled rootfs.
print('PASS: retained bootstrap never runs APT; missing/pending prerequisites fail; unknown bootstrap modes refused')
