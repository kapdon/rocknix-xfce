#!/usr/bin/env python3
"""Settings stays discoverable even when status tools are unavailable."""
import json
import os
from pathlib import Path
import subprocess

script = Path(__file__).resolve().parents[1] / 'rootfs-overlay/usr/local/bin/rocknix-status'
for width in ('640', '960', '1280', '1920', 'invalid'):
    result = subprocess.run(['/bin/sh', str(script)], check=True,
                            capture_output=True, text=True,
                            env={**os.environ, 'PATH': '/nonexistent',
                                 'ROCKNIX_LOGICAL_WIDTH': width})
    state = json.loads(result.stdout)
    assert state['text'] == 'Settings', state
    assert 'Open network, audio, display, gamescope or layout settings' in state['tooltip']
print('PASS: explicit Settings label at every width; details remain in tooltip')
