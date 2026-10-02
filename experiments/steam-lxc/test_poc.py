#!/usr/bin/env python3
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from discovery import Invalid, Snapshot, libraries, plan
from lease import Busy, Lease

CLIENT = '/storage/games-internal/roms/steam'
EXTERNAL = '/media/SD Card/SteamLibrary'
ROOTS = [CLIENT, EXTERNAL, '/storage/.steam']


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for name in ROOTS + ['/storage/.local/share', '/storage/roms', CLIENT + '/steamapps',
                             CLIENT + '/steamrtarm64']:
            self.path(name).mkdir(parents=True, exist_ok=True)
        self.path('/storage/.local/share/Steam').symlink_to(CLIENT)
        self.path('/storage/Steam').symlink_to('.local/share/Steam')
        self.path('/storage/roms/steam').symlink_to(CLIENT)
        self.path('/storage/.steam/steam').symlink_to('/storage/.local/share/Steam')
        self.path(CLIENT + '/steamrtarm64/steam').write_bytes(b'fixture-not-executable')
        self.path(CLIENT + '/steamapps/libraryfolders.vdf').write_text(
            '"libraryfolders" { "0" {"path" "' + CLIENT + '"} '
            '"1" { "path" "' + EXTERNAL + '" "apps" { "123" "5" } } }')
        self.snapshot = Snapshot(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def path(self, value):
        return self.root / value.lstrip('/')

    def test_resolves_absolute_and_relative_aliases(self):
        report = plan(self.snapshot, ROOTS)
        self.assertEqual(report['blockers'], [])
        self.assertEqual(len(report['mount_candidates']), 3)
        self.assertEqual(report['client'], CLIENT)
        self.assertTrue(report['arm64_client_present'])
        self.assertEqual(self.snapshot.resolve('/storage/.steam/steam'), CLIENT)

    def test_reads_without_altering_metadata_or_data(self):
        def signature():
            return {str(p): (p.lstat().st_uid, p.lstat().st_gid,
                p.lstat().st_mode, p.lstat().st_mtime_ns,
                os.readlink(p) if p.is_symlink() else
                hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None)
                for p in self.root.rglob('*')}
        before = signature()
        plan(self.snapshot, ROOTS)
        self.assertEqual(before, signature())

    def test_external_library_needs_exact_review(self):
        report = plan(self.snapshot, [CLIENT, '/storage/.steam'])
        self.assertTrue(any(EXTERNAL in text for text in report['blockers']))
        self.assertNotIn(EXTERNAL, [m['source'] for m in report['mount_candidates']])

    def test_external_symlink_requires_resolved_root(self):
        self.path('/media/alias').symlink_to(EXTERNAL)
        self.path(CLIENT + '/steamapps/libraryfolders.vdf').write_text(
            '"libraryfolders" { "1" "/media/alias" }')
        report = plan(self.snapshot, ROOTS)
        self.assertIn({'path': '/media/alias', 'target': EXTERNAL}, report['aliases'])

    def test_missing_library_blocks_complete_plan(self):
        self.path(EXTERNAL).rmdir()
        self.assertTrue(plan(self.snapshot, ROOTS)['blockers'])

    def test_ambiguous_installations(self):
        self.path('/storage/Steam').unlink()
        self.path('/storage/Steam').mkdir()
        self.assertIn('ambiguous', plan(self.snapshot, ROOTS)['blockers'][0])

    def test_links_never_read_host_absolute_targets(self):
        self.path('/escape').symlink_to('/etc/passwd')
        with self.assertRaises(FileNotFoundError):
            self.snapshot.local('/escape')
        self.path('/etc').mkdir()
        self.path('/etc/passwd').write_text('fixture')
        self.assertEqual(self.snapshot.local('/escape').read_text(), 'fixture')
        self.path(CLIENT + '/bad-link').symlink_to('/etc/passwd')
        self.assertTrue(any('outside reviewed' in b for b in plan(self.snapshot, ROOTS)['blockers']))

    def test_cycle_and_traversal(self):
        self.path('/loop').symlink_to('/loop')
        self.path('/up').symlink_to('../../outside')
        for value in ('/loop', '/up', '/storage/../etc', '/bad\npath'):
            with self.assertRaises(Invalid):
                self.snapshot.resolve(value)

    def test_broad_approvals_rejected(self):
        for path in ('/', '/storage', '/storage/scripts', '/storage/rocknix-desktop',
                     '/storage/games-internal', '/etc'):
            with self.assertRaises(Invalid):
                plan(self.snapshot, [path])

    def test_modern_legacy_and_malformed_vdf(self):
        self.assertEqual(libraries('// note\n"libraryfolders" { "1" "/space path" }'), ['/space path'])
        for text in ('"libraryfolders" {', '"libraryfolders" { "1" "relative" }',
                     '"libraryfolders" { "1" "a" "1" "b" }',
                     '"libraryfolders" { "1" {} }', 'garbage',
                     '"libraryfolders" {"1" {"path" "/ok"}} trailing'):
            with self.assertRaises(Invalid):
                libraries(text)


class LeaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.root.chmod(0o700)
        self.empty = True

    def tearDown(self):
        self.temp.cleanup()

    def lease(self, side):
        return Lease(self.root, side, lambda: self.empty)

    def test_both_directions(self):
        for side, other in [('native', 'lxc'), ('lxc', 'native')]:
            first = self.lease(side).acquire()
            try:
                with self.assertRaises(BlockingIOError):
                    self.lease(other).acquire()
            finally:
                first.release()

    def test_descendants_and_recovery(self):
        first = self.lease('lxc').acquire()
        self.empty = False
        with self.assertRaises(Busy):
            first.release()
        first.close_fd()  # Supervisor crash model: marker survives, lock releases.
        with self.assertRaises(Busy):
            Lease.recover(self.root, lambda: self.empty)
        self.empty = True
        with self.assertRaises(Busy):
            self.lease('native').acquire()
        Lease.recover(self.root, lambda: self.empty)
        self.lease('native').acquire().release()

    def test_unknown_detector_fails_closed(self):
        def unknown():
            raise OSError('cannot inspect scope')
        with self.assertRaises(OSError):
            Lease(self.root, 'lxc', unknown).acquire()

    def test_real_process_race_and_crash(self):
        code = '''import sys, time
from lease import Lease, Busy
try:
    held = Lease(sys.argv[1], sys.argv[2], lambda: True).acquire()
except (Busy, BlockingIOError):
    print('busy', flush=True)
else:
    print('held', flush=True)
    sys.stdin.readline()
    held.release()
'''
        children = [subprocess.Popen([sys.executable, '-c', code, str(self.root), side],
                    cwd=Path(__file__).parent, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    text=True) for side in ('native', 'lxc')]
        try:
            results = [p.stdout.readline().strip() for p in children]
            self.assertEqual(sorted(results), ['busy', 'held'])
            winner = children[results.index('held')]
            winner.kill()
            winner.wait(timeout=5)
            with self.assertRaises(Busy):
                self.lease('native').acquire()
            Lease.recover(self.root, lambda: True)
            self.lease('lxc').acquire().release()
        finally:
            for child in children:
                if child.poll() is None:
                    child.kill()
                child.wait(timeout=5)
                child.stdin.close()
                child.stdout.close()


if __name__ == '__main__':
    unittest.main()
