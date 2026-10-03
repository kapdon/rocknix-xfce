#!/usr/bin/python3
"""Exercise shared geometry policy, guest execution and the settings menu."""
import copy
import json
import os
from pathlib import Path
import runpy
import tempfile
import time
import unittest
from unittest.mock import patch

api = runpy.run_path('rootfs-overlay/usr/local/bin/rocknix-gamescope')
args = api['display_args']
main = api['main']
menu = runpy.run_path('rootfs-overlay/usr/local/bin/rocknix-games')


def area(height=953, scale=1):
    return {'format': 1, 'updated_at': time.time(),
            'output': {'rect': {'width': 1920, 'height': 1080}, 'scale': scale},
            'workspace': {'width': 1920, 'height': 1000},
            'client': {'width': 1920, 'height': height}}


class Display(unittest.TestCase):
    def test_sizes_and_scale(self):
        for height in (953, 575):
            self.assertEqual(args(True, area(height)),
                             ['-W', '1920', '-H', str(height), '-w', '1920', '-h', str(height)])
        self.assertEqual(args(True, area(scale=1.25)),
                         ['-W', '2400', '-H', '1191', '-w', '2400', '-h', '1191'])
        empty = area(); empty['client'] = None
        self.assertEqual(args(True, empty)[3], '1000')
        self.assertEqual(args(False, area()), ['-W','1920','-H','1080','-w','1920','-h','1080'])
        self.assertEqual(args(False, area(height=575))[3], '1080')

    def test_bad_or_stale_size_is_not_a_silent_720p_fallback(self):
        variants = [None, {}, dict(area(), updated_at=0), dict(area(), updated_at=float('nan'))]
        for bad in (0, -1, True, '953', 32768, 1001):
            value = area(); value['client']['height'] = bad; variants.append(value)
        for bad in (0, True, '1', float('nan'), 5):
            value = area(); value['output']['scale'] = bad; variants.append(value)
        for value in variants:
            with self.subTest(value=value), self.assertRaises((ValueError, KeyError)):
                args(True, value)

    def test_command_remains_argv_and_uses_guest_backend(self):
        with tempfile.TemporaryDirectory() as tmp:
            bridge = Path(tmp)
            (bridge / 'games.json').write_text(json.dumps({'virtual_display': True}))
            (bridge / 'workarea.json').write_text(json.dumps(area()))
            with patch.dict(api['configured_args'].__globals__, BRIDGE=bridge), patch('os.execve') as execute, \
                    patch.dict(os.environ, PATH='/usr/local/bin:/usr/bin'):
                command = ['wine', '/games/a game.exe', '$(touch /tmp/unsafe)']
                main(['--', *command])
                binary, argv, env = execute.call_args.args
                self.assertEqual(binary, '/usr/games/gamescope')
                self.assertEqual(argv[1:3], ['--backend', 'sdl'])
                self.assertEqual(argv[-len(command):], command)
                self.assertIn('953', argv)
                self.assertEqual(env['SDL_VIDEODRIVER'], 'wayland')
                self.assertEqual(env['PATH'], '/usr/local/bin:/usr/bin:/usr/games')
                self.assertEqual(env['DISABLE_GAMESCOPE_WSI'], '1')
                # Off uses the full monitor, independent of the current client size.
                main(['--virtual-display', 'off', '--', *command])
                self.assertIn('1080', execute.call_args.args[1])
                (bridge / 'games.json').write_text('{}')
                main(['--', *command])
                self.assertIn('953', execute.call_args.args[1])

    def test_toggle_menu_round_trip(self):
        for enabled in (True, False):
            state = {'mode': 'keep', 'virtual_display': enabled}
            sent = []
            def send(*words):
                sent.append(words)
                if words[0] == 'virtual-display': state['virtual_display'] = words[1] == 'on'
            def choose(prompt, choices):
                self.assertIn('Virtual display', choices[0][0])
                return choices[0][1]
            with patch.dict(menu['main'].__globals__, state=lambda: copy.copy(state), send=send, menu=choose), \
                    patch('sys.argv', ['rocknix-games', 'settings']), patch('time.sleep'):
                menu['main']()
            self.assertEqual(sent, [('refresh',), ('virtual-display', 'off' if enabled else 'on')])
            self.assertEqual(state['mode'], 'keep')


if __name__ == '__main__':
    unittest.main()
