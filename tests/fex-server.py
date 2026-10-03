#!/usr/bin/python3
"""Readiness is delivered after the native server handshake; stop is forwarded."""
import os
from pathlib import Path
import signal
import socket
import subprocess
import tempfile
import unittest

SOURCE = Path('rootfs-overlay/usr/local/bin/rocknix-fex-server')


class Server(unittest.TestCase):
    def test_readiness_and_termination(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            server = root / 'server'
            server.write_text('''#!/usr/bin/python3
import os, signal, sys, time
from pathlib import Path
assert sys.argv[-1] == '-p'
fd = int(next(x.split('=',1)[1] for x in sys.argv if x.startswith('--wait_pipe=')))
def stop(sig, frame):
 Path(os.environ['MARKER']).write_text('stopped')
 raise SystemExit(0)
signal.signal(signal.SIGTERM, stop)
os.close(fd)
while True: time.sleep(.1)
''')
            server.chmod(0o755)
            helper = root / 'helper'
            helper.write_text(SOURCE.read_text().replace('/run/rocknix-fex/bin/FEXServer', str(server)))
            helper.chmod(0o755)
            address = str(root / 'notify')
            with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as notify:
                notify.bind(address)
                notify.settimeout(5)
                process = subprocess.Popen([str(helper)], env=dict(os.environ, NOTIFY_SOCKET=address, MARKER=str(root/'stopped')))
                try:
                    self.assertEqual(notify.recv(100), b'READY=1')
                    process.send_signal(signal.SIGTERM)
                    self.assertEqual(process.wait(timeout=5), 0)
                    self.assertEqual((root/'stopped').read_text(), 'stopped')
                finally:
                    if process.poll() is None:
                        process.kill(); process.wait()


if __name__ == '__main__': unittest.main()
