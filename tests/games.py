#!/usr/bin/python3
"""Validate the guest-to-host launch boundary and durable game recovery."""
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import runpy
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
source() {
  if [[ $1 == /usr/bin/start_steam.sh ]]; then
    steam_scope_reexec_if_needed() {
      [[ $STEAM_MAIN_SCRIPT == /* && $1 =~ ^[0-9]+$ && $2 == keep ]] || exit 9
      printf 'NATIVE_SCOPE_HELPER\\n'
    }
  fi
}
exec() {
  [[ $USER == fixture-user && $LOGNAME == fixture-login ]] || exit 10
  if [[ $2 == /native/Game.desktop ]]; then
    [[ ! -v _STEAM_SCOPE ]] || exit 11
  fi
  printf 'WSI=%s DISABLE=%s\\n' "${ENABLE_GAMESCOPE_WSI-unset}" "${DISABLE_GAMESCOPE_WSI-unset}"
  printf '%s\\n' "$@"
  exit
}
/usr/bin/gamescope() { exec /usr/bin/gamescope "$@"; }
builtin source "$@"
'''
            env=dict(os.environ,ENABLE_GAMESCOPE_WSI='1',USER='fixture-user',LOGNAME='fixture-login',_STEAM_SCOPE='1')
            env.pop('DISABLE_GAMESCOPE_WSI',None)
            for app in ('526870','123','12345678901234567890'):
                for mode in ('close','keep'):
                    result=subprocess.run(['bash','-c',harness,str(script),str(script),app,mode],env=env,text=True,capture_output=True,check=True).stdout.splitlines()
                    if mode=='keep':
                        self.assertEqual(result.pop(0),'NATIVE_SCOPE_HELPER')
                    self.assertEqual(result[0],'WSI=0 DISABLE=1')
                    if mode=='close':
                        self.assertEqual(result[1:3],['/usr/bin/runemu.sh','/native/Game.desktop'])
                    else:
                        self.assertEqual(result[1],'/usr/bin/gamescope')
                        self.assertIn('wayland',result)

    def test_keep_restarts_only_for_steam_exit_42(self):
        script=str(Path('payload/bin/rocknix-games-session').resolve())
        harness=r'''
source() {
  if [[ $1 == /usr/bin/start_steam.sh ]]; then
    steam_scope_reexec_if_needed() { printf 'scope\n' >> "$FIXTURE_DIR/scopes"; }
  fi
}
mktemp() { command mktemp -d "$FIXTURE_DIR/scratch.XXXXXX"; }
/usr/bin/gamescope() {
  printf 'gamescope\n' >> "$FIXTURE_DIR/compositors"
  if [[ $FIXTURE_MODE != no-client ]]; then
    while [[ $1 != -- ]]; do shift; done
    shift
    local -a command=()
    local argument
    for argument; do
      [[ $argument != /storage/.local/share/Steam/steamrtarm64/steam ]] || argument=$FIXTURE_DIR/steam
      command+=("$argument")
    done
    "${command[@]}" || :
    [[ $FIXTURE_MODE != stop ]] || kill -TERM "$$"
  fi
  return "$FIXTURE_COMPOSITOR_STATUS"
}
exec() { "$@"; exit $?; }
builtin source "$1" 526870 keep
'''
        cases = (
            ([0], 0, 'normal', 1, 0),
            ([42, 0], 0, 'normal', 2, 0),
            ([42, 42, 0], 1, 'normal', 3, 1),
            ([42, 7], 0, 'normal', 2, 7),
            ([0], 42, 'normal', 1, 42),
            ([], 42, 'no-client', 1, 42),
            ([42], 0, 'stop', 1, 143),
        )
        for statuses, compositor_status, mode, launches, expected in cases:
            with self.subTest(statuses=statuses, compositor=compositor_status, mode=mode), tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                (root/'statuses').write_text(json.dumps(statuses))
                steam=root/'steam'
                steam.write_text('''#!/usr/bin/python3
import json, os, sys
from pathlib import Path
root=Path(os.environ['FIXTURE_DIR'])
log=root/'clients'
calls=json.loads(log.read_text()) if log.exists() else []
statuses=json.loads((root/'statuses').read_text())
status=statuses[len(calls)]
calls.append(sys.argv[1:])
log.write_text(json.dumps(calls))
raise SystemExit(status)
''')
                steam.chmod(0o755)
                env=dict(os.environ,FIXTURE_DIR=tmp,FIXTURE_MODE=mode,
                         FIXTURE_COMPOSITOR_STATUS=str(compositor_status))
                result=subprocess.run(['bash','-c',harness,'fixture',script],env=env,
                                      text=True,capture_output=True,timeout=10)
                self.assertEqual(result.returncode,expected,result.stderr)
                self.assertEqual((root/'compositors').read_text().splitlines(),['gamescope']*launches)
                self.assertEqual((root/'scopes').read_text().splitlines(),['scope'])
                clients=json.loads((root/'clients').read_text()) if (root/'clients').exists() else []
                self.assertEqual(len(clients),len(statuses))
                for args in clients:
                    self.assertEqual(args,['-deckard','-steamos3','-nobigpicture','-noshaders','-silent','steam://rungameid/526870'])
                self.assertEqual(list(root.glob('scratch.*')),[])

    def test_missing_native_scope_helper_fails_closed(self):
        script=str(Path('payload/bin/rocknix-games-session').resolve())
        harness='source() { :; }; builtin source "$@"'
        result=subprocess.run(['bash','-c',harness,script,script,'526870','keep'],text=True,capture_output=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('ROCKNIX Steam scope helper is unavailable',result.stderr)

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

    def test_stop_after_native_exit_is_idempotent(self):
        with patch.object(g,'run',return_value=SimpleNamespace(returncode=5)),patch.object(g,'active',return_value=False),patch.object(g,'publish'):
            g.request(['stop'])
        with patch.object(g,'run',return_value=SimpleNamespace(returncode=1)),patch.object(g,'active',return_value=True),patch.object(g,'publish'):
            with self.assertRaisesRegex(ValueError,'Could not stop'):g.request(['stop'])

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

    def test_maintenance_excluded_through_recovery(self):
        idle=runpy.run_path('payload/bin/rocknix-desktop-maintenance')['require_games_idle']
        for recovered in (True,False):
            with self.subTest(recovered=recovered), tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                journal=root/'session.json'
                journal.write_text(json.dumps({'mode':'close','desktop_stopped':True,'binfmt':{},'scope':g.SCOPE}))
                states={g.UNIT:'deactivating',g.SCOPE:'active'}
                def systemctl(args,**kwargs):
                    return SimpleNamespace(stdout=states[args[-1]],returncode=0)
                def blocked():
                    with self.assertRaises(RuntimeError):idle()
                def recover_command(*args,**kwargs):
                    blocked()
                    if args[1:]==('stop',g.SCOPE):states[g.SCOPE]='inactive'
                    return SimpleNamespace(stdout=states[g.SCOPE] if args[1]=='show' else 'running')
                with patch('os.path.lexists',side_effect=lambda p: str(p)=='/run/rocknix-desktop-games/session.json' and journal.exists()), \
                        patch('subprocess.run',side_effect=systemctl), \
                        patch.object(g,'LEASE',root),patch.object(g,'CONTROL',root/'controls.json'), \
                        patch.object(g,'CONTROL_PUBLIC',root/'controller.json'), \
                        patch.object(g,'run',side_effect=recover_command), \
                        patch.object(g.time,'sleep',side_effect=lambda _:blocked()), \
                        patch.object(g,'active',return_value=recovered):
                    if recovered:g.recover()
                    else:
                        with self.assertRaisesRegex(ValueError,'Desktop recovery failed'):g.recover()
                    blocked()  # ExecStopPost has not yet left the deactivating unit.
                    states[g.UNIT]='inactive' if recovered else 'failed'
                    if recovered:
                        self.assertFalse(journal.exists())
                        idle()
                    else:
                        self.assertTrue(journal.exists())
                        blocked()

    def test_focus_requires_owned_process(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(g,'PROC',Path(tmp)):
            p=Path(tmp)/'123';p.mkdir()
            (p/'cgroup').write_text('0::/system.slice/' + g.SCOPE + '\n')
            self.assertTrue(g.focused_game({'floating_nodes':[{'focused':True,'pid':123}]}))
            self.assertFalse(g.focused_game({'focused':False,'pid':123}))
            self.assertFalse(g.focused_game({'focused':True,'pid':456,'name':'Steam'}))
            (p/'cgroup').write_text('0::/system.slice/fake-' + g.SCOPE + '\n')
            self.assertFalse(g.focused_game({'focused':True,'pid':123}))
            (p/'cgroup').write_text('0::/system.slice/' + g.UNIT + '\n')
            self.assertFalse(g.focused_game({'focused':True,'pid':123}))

    def test_native_scope_stops_before_recovery(self):
        for state in ('inactive','failed','active','deactivating',''):
            with tempfile.TemporaryDirectory() as tmp,patch.object(g,'LEASE',Path(tmp)),patch.object(g.time,'sleep'),patch.object(g,'active',return_value=True):
                journal=Path(tmp)/'session.json'
                journal.write_text(json.dumps({'mode':'close','desktop_stopped':True,'binfmt':{},'scope':g.SCOPE}))
                def invoke(*args,**kwargs):
                    return SimpleNamespace(stdout=state if args[1]=='show' else 'running')
                with patch.object(g,'run',side_effect=invoke) as run:
                    if state in ('inactive','failed'):
                        g.recover()
                        self.assertFalse(journal.exists())
                        self.assertEqual(run.call_args_list[0].args,('systemctl','stop',g.SCOPE))
                        self.assertEqual(run.call_args_list[-1].args,('systemctl','start','rocknix-desktop.service'))
                    else:
                        with self.assertRaisesRegex(ValueError,'scope did not stop'):g.recover()
                        self.assertTrue(journal.exists())
                        self.assertFalse(any(c.args[1]=='start' for c in run.call_args_list))

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

    def test_controls_without_game_lease(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(g,'CONTROL',Path(tmp)/'mode'),patch.object(g,'CONTROL_PUBLIC',Path(tmp)/'public'),patch.object(g,'LEASE',Path(tmp)/'absent'),patch.object(g,'control_profile') as profile,patch.object(g,'active',side_effect=lambda unit:unit=='rocknix-desktop.service'),patch.object(g,'publish'),patch.object(g.subprocess,'run') as sway:
            saved={'mode':'auto','controller':{'desktop':'desktop','game':'native'}}
            g.atomic(g.CONTROL,saved,0o600)
            g.atomic(g.CONTROL_PUBLIC,{'mode':'auto','active':'desktop'})
            g.request(['controls','game'])
            self.assertEqual(json.loads(g.CONTROL_PUBLIC.read_text()),{'mode':'game','active':'game'})
            profile.assert_called_once_with(dict(saved,mode='game'),'game')
            profile.reset_mock()
            # A manual choice survives future ticks without consulting focus.
            g.control_update();profile.assert_not_called();sway.assert_not_called()
            g.request(['controls','desktop'])
            self.assertEqual(json.loads(g.CONTROL_PUBLIC.read_text())['active'],'desktop')
            self.assertFalse(g.LEASE.exists())
            with patch.object(g,'active',return_value=False),self.assertRaisesRegex(ValueError,'Desktop'):
                g.request(['controls','game'])

    def test_controller_initializes_for_each_desktop(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(g,'BASE',Path(tmp)),patch.object(g,'INPUT_STATE',Path(tmp)/'input-state'),patch.object(g,'CONTROL',Path(tmp)/'mode'),patch.object(g,'CONTROL_PUBLIC',Path(tmp)/'public'):
            native=Path(tmp)/'native.yaml';native.touch()
            desktop=Path(tmp)/'input/desktop.yaml';desktop.parent.mkdir();desktop.touch()
            g.INPUT_STATE.write_text('profile='+str(native)+'\n')
            g.atomic(g.CONTROL,{'mode':'game'})
            g.control_begin()
            self.assertEqual(json.loads(g.CONTROL_PUBLIC.read_text()),{'mode':'auto','active':'desktop'})
            self.assertEqual(json.loads(g.CONTROL.read_text())['controller']['game'],str(native))
            self.assertEqual(g.CONTROL.stat().st_mode & 0o777,0o600)

    def test_keep_recovery_preserves_desktop_controller_selection(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(g,'LEASE',Path(tmp)),patch.object(g,'CONTROL',Path(tmp)/'mode'),patch.object(g,'CONTROL_PUBLIC',Path(tmp)/'public'),patch.object(g,'control_profile') as profile,patch.object(g,'active',return_value=True),patch.object(g,'run',return_value=SimpleNamespace(stdout='running')),patch.object(g,'publish'):
            saved={'mode':'keep','binfmt':{}}
            (Path(tmp)/'session.json').write_text(json.dumps(saved))
            g.atomic(g.CONTROL,{'mode':'game'})
            g.atomic(g.CONTROL_PUBLIC,{'mode':'game','active':'game'})
            g.recover()
            profile.assert_not_called()
            self.assertEqual(json.loads(g.CONTROL.read_text())['mode'],'game')
            self.assertEqual(json.loads(g.CONTROL_PUBLIC.read_text())['active'],'game')
            self.assertFalse((Path(tmp)/'session.json').exists())

    def test_no_restart_during_host_shutdown(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(g,'LEASE',Path(tmp)),patch.object(g,'run',return_value=SimpleNamespace(stdout='stopping')) as run:
            (Path(tmp)/'session.json').write_text(json.dumps({'mode':'close','desktop_stopped':True,'binfmt':{}}))
            g.recover();self.assertEqual(run.call_count,1)

if __name__=='__main__':unittest.main()
