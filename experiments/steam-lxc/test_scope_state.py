#!/usr/bin/env python3
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from lease import Busy, Lease
from scope_state import ScopeSet, Unknown, populated


class ScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.cgroups = self.root / 'cgroups'
        self.names = ('system.slice/steam-bigpicture.scope', 'desktop-steam')
        for name in self.names:
            (self.cgroups / name).mkdir(parents=True)
            (self.cgroups / name / 'cgroup.events').write_text('populated 0\nfrozen 0\n')
        self.reader = ScopeSet(self.cgroups, self.names, owner=os.getuid())
        self.state = self.root / 'lease'
        self.state.mkdir(mode=0o700)

    def tearDown(self):
        self.temp.cleanup()

    def event(self, index, text):
        (self.cgroups / self.names[index] / 'cgroup.events').write_text(text)

    def test_two_empty_scopes(self):
        self.assertTrue(self.reader.empty())
        lease = Lease(self.state, 'lxc', self.reader.empty).acquire()
        lease.release()

    def test_descendant_population_blocks_even_with_empty_direct_pid_list(self):
        # Kernel populated includes descendants; cgroup.procs does not.
        scope = self.cgroups / self.names[0]
        (scope / 'cgroup.procs').write_text('')
        (scope / 'game').mkdir()
        (scope / 'game/cgroup.procs').write_text('1234\n')
        self.event(0, 'populated 1\nfrozen 0\n')
        self.assertFalse(self.reader.empty())
        with self.assertRaises(Busy):
            Lease(self.state, 'lxc', self.reader.empty).acquire()

    def test_orphan_blocks_release_and_recovery(self):
        lease = Lease(self.state, 'lxc', self.reader.empty).acquire()
        self.event(1, 'populated 1\n')
        with self.assertRaises(Busy):
            lease.release()
        lease.close_fd()
        with self.assertRaises(Busy):
            Lease.recover(self.state, self.reader.empty)
        self.assertTrue((self.state / 'active').exists())
        self.event(1, 'populated 0\n')
        Lease.recover(self.state, self.reader.empty)
        Lease(self.state, 'native', self.reader.empty).acquire().release()

    def test_missing_scope_or_event_is_unknown(self):
        event = self.cgroups / self.names[1] / 'cgroup.events'
        event.unlink()
        with self.assertRaises(Unknown):
            self.reader.empty()
        event.parent.rmdir()
        with self.assertRaises(Unknown):
            self.reader.empty()

    def test_symlink_and_writable_scope_rejected(self):
        scope = self.cgroups / self.names[1]
        original = scope.with_name('original')
        scope.rename(original)
        scope.symlink_to(original)
        with self.assertRaises(Unknown):
            self.reader.empty()
        scope.unlink()
        original.rename(scope)
        scope.chmod(0o777)
        with self.assertRaises(Unknown):
            self.reader.empty()

    def test_malformed_or_untrusted_event_rejected(self):
        for text in ('', 'populated 2', 'populated 0\npopulated 1', 'populated',
                     'other 0', 'populated 0\n' + 'x' * 4096):
            self.event(0, text)
            with self.assertRaises(Unknown):
                self.reader.empty()
        self.event(0, 'populated 0\n')
        (self.cgroups / self.names[0] / 'cgroup.events').chmod(0o666)
        with self.assertRaises(Unknown):
            self.reader.empty()

    def test_fifo_event_refused_without_waiting_for_writer(self):
        event = self.cgroups / self.names[0] / 'cgroup.events'
        event.unlink()
        os.mkfifo(event, 0o600)
        with self.assertRaises(Unknown):
            self.reader.empty()

    def test_replacement_and_population_between_samples(self):
        actual = self.reader._sample
        calls = 0
        def changed(fd, name):
            nonlocal calls
            calls += 1
            identity, state = actual(fd, name)
            return ((identity[0], identity[1] + 1), state) if calls == 3 else (identity, state)
        with patch.object(self.reader, '_sample', side_effect=changed):
            with self.assertRaises(Unknown):
                self.reader.empty()
        calls = 0
        def appeared(fd, name):
            nonlocal calls
            calls += 1
            identity, state = actual(fd, name)
            return identity, state or calls == 3
        with patch.object(self.reader, '_sample', side_effect=appeared):
            self.assertFalse(self.reader.empty())

    def test_unknown_during_recovery_preserves_marker(self):
        lease = Lease(self.state, 'lxc', self.reader.empty).acquire()
        lease.close_fd()
        self.event(1, 'bad')
        with self.assertRaises(Unknown):
            Lease.recover(self.state, self.reader.empty)
        self.assertTrue((self.state / 'active').exists())

    def test_configuration_and_future_event_fields(self):
        for names in (('one',), ('same', 'same'), ('one', '../two'), ('one', '/two')):
            with self.assertRaises(ValueError):
                ScopeSet(self.cgroups, names)
        self.assertFalse(populated('populated 0\nfrozen 0\nfuture 12\n'))


if __name__ == '__main__':
    unittest.main()
