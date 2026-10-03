#!/usr/bin/env python3
"""Deliberately SIGKILL this updater process during host activation on reserved RP6.

Desktop must already be inactive. Uses the installed updater, inserting one
fault immediately after a real atomic launcher replacement. Resume afterward
with the same verified bundle/checksum using the ordinary installed updater.
The updater retains its normal rollback copy; no journal bypass is made. This is NOT a power-loss test.
"""
import json
import os
from pathlib import Path
import runpy
import signal


def main():
    assert os.geteuid() == 0
    base = Path('/storage/rocknix-desktop/managed/host')
    assert not os.path.lexists(base / 'state/upgrade-in-progress.json')
    api = runpy.run_path(str(base / 'bin/rocknix-lxc-upgrade'))
    namespace = api['main'].__globals__
    original = namespace['atomic']

    def interrupted_atomic(path, data, mode=0o644):
        original(path, data, mode)
        if path == base / 'bin/launch-sway-desktop':
            record = json.loads(namespace['GUARD'].read_text())
            assert record['phase'] == 'activating'
            assert not namespace['STATE'].exists(), 'maintenance must already be closed'
            assert path.read_bytes() == data
            print('INJECT: SIGKILL after atomic host launcher activation; '
                  'persistent replacement journal remains', flush=True)
            os.kill(os.getpid(), signal.SIGKILL)

    namespace['atomic'] = interrupted_atomic
    api['main']()
    raise RuntimeError('Fault injection was not reached')


if __name__ == '__main__':
    main()
