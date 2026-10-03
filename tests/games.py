#!/usr/bin/python3
"""Validate the guest-to-host launch boundary and durable game recovery."""
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

loader=importlib.machinery.SourceFileLoader('games','payload/bin/rocknix-games')
spec=importlib.util.spec_from_loader(loader.name,loader)
g=importlib.util.module_from_spec(spec);loader.exec_module(g)

class Games(unittest.TestCase):
    def test_session_shared_wsi_policy_and_native_routing(self):
        # Execute the real shell branches, replacing external launch commands.
        # Inherit WSI=1 to exercise precedence over a pre-enabled layer.
        with tempfile.TemporaryDirectory() as tmp:
            script=Path(tmp)/'rocknix-games-session'
            script.write_bytes(Path('payload/bin/rocknix-games-session').read_bytes())
            helper=Path(tmp)/'rocknix-games'
            helper.write_text('#!/bin/sh\nprintf "/native/Game.desktop\\n"\n')
            helper.chmod(0o755)
            harness='''
source() { :; }
exec() {
  printf 'WSI=%s DISABLE=%s\\n' "${ENABLE_GAMESCOPE_WSI-unset}" "${DISABLE_GAMESCOPE_WSI-unset}"
  printf '%s\\n' "$@"
  exit
}
builtin source "$@"
'''
            env=dict(os.environ,ENABLE_GAMESCOPE_WSI='1')
            env.pop('DISABLE_GAMESCOPE_WSI',None)
            for app in ('526870','123','12345678901234567890'):
                for mode in ('close','keep'):
                    result=subprocess.run(['bash','-c',harness,str(script),str(script),app,mode],env=env,text=True,capture_output=True,check=True).stdout.splitlines()
                    self.assertEqual(result[0],'WSI=0 DISABLE=1')
                    if mode=='close':
                        self.assertEqual(result[1:3],['/usr/bin/runemu.sh','/native/Game.desktop'])
                    else:
                        self.assertEqual(result[1],'/usr/bin/gamescope')
                        self.assertIn('wayland',result)

    def test_catalog_tracks_native_shortcuts(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(g,'SHORTCUTS',Path(tmp)):
            p=Path(tmp)/'Satisfactory.desktop'
            p.write_text('[Desktop Entry]\nName=Satisfactory\nExec=steam steam://rungameid/526870\n')
            (Path(tmp)/'Steam.desktop').write_text('')
            (Path(tmp)/'unsafe.desktop').write_text('[Desktop Entry]\nName=Bad\nExec=steam steam://rungameid/1; touch /tmp/unsafe\n')
            self.assertEqual(g.catalog(),[{'id':'526870','name':'Satisfactory'}])
            self.assertEqual(g.shortcut('526870'),str(p))
            p.unlink()
            self.assertEqual(g.catalog(),[])
            with self.assertRaises(ValueError): g.shortcut('526870')
            p.write_text('[Desktop Entry]\nName=Custom game\nExec=steam steam://rungameid/12345678901234567890\n')
            self.assertEqual(g.catalog()[0]['name'],'Custom game')

    def test_reject_requests(self):
        with patch.object(g,'catalog',return_value=[{'id':'526870','name':'Satisfactory'}]),patch.object(g,'run') as run:
            for words in [['launch','526870;id','close'],['launch','526870','other'],['mode','keep;id'],['launch','123','keep'],['launch','526870','close','extra']]:
                with self.assertRaises(ValueError):g.request(words)
            run.assert_not_called()

    def test_persist_modes(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(g,'STATE',Path(tmp)/'games.json'),patch.object(g,'publish'):
            self.assertEqual(g.mode(),'close')
            for mode in g.MODES:
                g.request(['mode',mode]);self.assertEqual(g.mode(),mode)

    def test_existing_steam_rejected(self):
        with patch.object(g,'catalog',return_value=[{'id':'526870'}]),patch.object(g,'active',return_value=False),patch.object(g,'steam_running',return_value=True),patch.object(g,'run') as run:
            with self.assertRaises(ValueError):g.request(['launch','526870','close'])
            run.assert_not_called()

    def test_independent_service_and_keep_binding(self):
        for mode in g.MODES:
            with patch.object(g,'catalog',return_value=[{'id':'526870'}]),patch.object(g,'active',side_effect=lambda u:u=='rocknix-desktop.service'),patch.object(g,'steam_running',return_value=False),patch.object(g,'run') as run,patch.object(g,'publish'):
                g.request(['launch','526870',mode])
                args=run.call_args.args
                self.assertIn('--property=KillMode=control-group',args)
                self.assertIn(f'--property=ExecStopPost={g.BASE}/bin/rocknix-games recover',args)
                if mode == 'close':
                    self.assertFalse(any('sway.service' in a for a in args))
                self.assertEqual(args[-3:],('session','526870',mode))
                self.assertEqual('--property=BindsTo=rocknix-desktop.service sway.service' in args,mode=='keep')

    def test_close_recovery_restarts_essway_before_desktop(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(g,'LEASE',Path(tmp)),patch.object(g.time,'sleep'),patch.object(g,'active',return_value=True),patch.object(g,'run',return_value=SimpleNamespace(stdout='running')) as run:
            p=Path(tmp)/'session.json';p.write_text(json.dumps({'mode':'close','desktop_stopped':True,'binfmt':{}}))
            g.recover()
            self.assertEqual(run.call_args_list[-2].args,('systemctl','start','essway.service'))
            self.assertEqual(run.call_args_list[-1].args,('systemctl','start','rocknix-desktop.service'))
            self.assertFalse(p.exists())

    def test_failed_desktop_recovery_retains_lease(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(g,'LEASE',Path(tmp)),patch.object(g.time,'sleep'),patch.object(g,'active',return_value=False),patch.object(g,'run',return_value=SimpleNamespace(stdout='running')):
            p=Path(tmp)/'session.json'
            p.write_text(json.dumps({'mode':'close','desktop_stopped':True,'binfmt':{}}))
            with self.assertRaisesRegex(ValueError,'recovery failed'):
                g.recover()
            self.assertTrue(p.exists())

    def test_focus_requires_owned_process(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(g,'PROC',Path(tmp)):
            p=Path(tmp)/'123';p.mkdir()
            (p/'cgroup').write_text('0::/system.slice/' + g.UNIT + '\n')
            self.assertTrue(g.focused_game({'floating_nodes':[{'focused':True,'pid':123}]}))
            self.assertFalse(g.focused_game({'focused':False,'pid':123}))
            self.assertFalse(g.focused_game({'focused':True,'pid':456,'name':'Steam'}))
            (p/'cgroup').write_text('0::/system.slice/fake-' + g.UNIT + '\n')
            self.assertFalse(g.focused_game({'focused':True,'pid':123}))

    def test_manual_override_and_auto(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(g,'CONTROL',Path(tmp)/'mode'),patch.object(g,'CONTROL_PUBLIC',Path(tmp)/'public'),patch.object(g,'control_profile') as profile,patch.object(g.subprocess,'run',return_value=SimpleNamespace(stdout='{}')),patch.object(g,'focused_game',return_value=True):
            g.atomic(g.CONTROL,{'mode':'desktop'})
            self.assertEqual(g.control_tick({},'game'),'desktop')
            profile.assert_called_once_with({},'desktop')
            profile.reset_mock()
            g.control_tick({},'desktop');profile.assert_not_called()
            g.atomic(g.CONTROL,{'mode':'auto'})
            self.assertEqual(g.control_tick({},'desktop'),'game')
            self.assertEqual(json.loads(g.CONTROL_PUBLIC.read_text())['mode'],'auto')

    def test_keep_recovery_restores_controller(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(g,'LEASE',Path(tmp)),patch.object(g,'CONTROL',Path(tmp)/'mode'),patch.object(g,'CONTROL_PUBLIC',Path(tmp)/'public'),patch.object(g,'control_profile') as profile,patch.object(g,'active',return_value=True),patch.object(g,'run',return_value=SimpleNamespace(stdout='running')),patch.object(g,'publish'):
            saved={'mode':'keep','binfmt':{},'controller':{'desktop':'desktop','game':'native'}}
            (Path(tmp)/'session.json').write_text(json.dumps(saved))
            g.recover()
            profile.assert_called_once_with(saved,'desktop')
            self.assertFalse((Path(tmp)/'session.json').exists())

    def test_no_restart_during_host_shutdown(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(g,'LEASE',Path(tmp)),patch.object(g,'run',return_value=SimpleNamespace(stdout='stopping')) as run:
            (Path(tmp)/'session.json').write_text(json.dumps({'mode':'close','desktop_stopped':True,'binfmt':{}}))
            g.recover();self.assertEqual(run.call_count,1)

if __name__=='__main__':unittest.main()
