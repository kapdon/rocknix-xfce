import unittest
from elf_metadata import dynamic


class DynamicTests(unittest.TestCase):
    def test_gnu(self):
        self.assertEqual(dynamic('''
 0x0000000000000001 (NEEDED) Shared library: [libc.so.6]
 0x000000000000001d (RUNPATH) Library runpath: [$ORIGIN]
'''), {'needed': ['libc.so.6'], 'runpath': ['$ORIGIN'], 'rpath': []})

    def test_elfutils(self):
        self.assertEqual(dynamic('''
  NEEDED            Shared library: [libc.so.6]
  NEEDED            libdl.so.2
  RUNPATH           Library runpath: [$ORIGIN]
'''), {'needed': ['libc.so.6', 'libdl.so.2'],
       'runpath': ['$ORIGIN'], 'rpath': []})

    def test_fail_closed(self):
        for value in ('', 'NEEDED', '(NEEDED) malformed', 'NEEDED a b'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                dynamic(value)


if __name__ == '__main__':
    unittest.main()
