#!/usr/bin/env python3
import os
from pathlib import Path
import tempfile
import unittest
from lease import Busy, Lease


class LeaseFilesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.state = self.root / 'state'
        self.state.mkdir(mode=0o700)

    def tearDown(self):
        self.temp.cleanup()

    def test_reacquire_preserves_original_lock(self):
        lease = Lease(self.state, 'lxc', lambda: True).acquire()
        try:
            with self.assertRaises(RuntimeError):
                lease.acquire()
            with self.assertRaises(Busy):
                Lease(self.state, 'native', lambda: True).acquire()
        finally:
            lease.release()
        Lease(self.state, 'native', lambda: True).acquire().release()

    def test_ancestor_and_terminal_symlinks_refused(self):
        alias = self.root / 'alias'
        alias.symlink_to(self.state)
        parent_alias = self.root / 'parent'
        parent_alias.symlink_to(self.root)
        for path in (alias, parent_alias / 'state'):
            with self.assertRaises(OSError):
                Lease(path, 'lxc', lambda: True).acquire()

    def test_lock_symlink_hardlink_and_fifo_refused(self):
        target = self.root / 'target'
        target.write_text('unchanged')
        target.chmod(0o600)
        lock = self.state / 'lock'
        for kind in ('symlink', 'hardlink', 'fifo'):
            if kind == 'symlink':
                lock.symlink_to(target)
            elif kind == 'hardlink':
                os.link(target, lock)
            else:
                os.mkfifo(lock, 0o600)
            with self.assertRaises((OSError, ValueError)):
                Lease(self.state, 'lxc', lambda: True).acquire()
            lock.unlink()
        self.assertEqual(target.read_text(), 'unchanged')

    def test_recovery_refuses_bad_marker_without_removing_it(self):
        lease = Lease(self.state, 'lxc', lambda: True).acquire()
        lease.close_fd()
        marker = self.state / 'active'
        marker.unlink()
        marker.symlink_to(self.root / 'missing')
        with self.assertRaises(OSError):
            Lease.recover(self.state, lambda: True)
        self.assertTrue(marker.is_symlink())
        marker.unlink()
        marker.write_text('lxc\n')
        marker.chmod(0o666)
        with self.assertRaises(ValueError):
            Lease.recover(self.state, lambda: True)
        self.assertTrue(marker.exists())

    def test_stable_inode_and_private_marker(self):
        lease = Lease(self.state, 'lxc', lambda: True).acquire()
        original = (self.state / 'lock').stat().st_ino
        self.assertEqual((self.state / 'active').stat().st_mode & 0o777, 0o600)
        lease.release()
        Lease.recover(self.state, lambda: True)
        other = Lease(self.state, 'native', lambda: True).acquire()
        other.release()
        self.assertEqual((self.state / 'lock').stat().st_ino, original)


if __name__ == '__main__':
    unittest.main()
