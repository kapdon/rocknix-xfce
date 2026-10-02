#!/usr/bin/env python3
"""RP6 stage-1 experiment, NOT a production launcher.

Stops Desktop and boots the installed rootfs without Desktop home/shared mounts.
Uses disposable ext4 fixtures, read-only native runtime, and a COPIED lock file.
Leaves EmulationStation active; never starts Steam. Requires device authorization.
Exact tested installed revision and interpretation: DEVICE-TESTS.md.
"""
import sys
if __name__ != '__main__' or sys.argv[1:] != ['--run-on-rp6-dev']:
    raise SystemExit('explicit --run-on-rp6-dev required; read DEVICE-TESTS.md first')
from pathlib import Path
import os,runpy,subprocess,json,tempfile,shutil,signal
host=Path('/storage/rocknix-desktop/managed/host')
module=runpy.run_path(str(host/'bin/rocknix-lxc'))
source=Path(tempfile.mkdtemp(prefix='rocknix-steam-poc-',dir='/storage'))
source.chmod(0o755)
fixture=source/'fixture';fixture.mkdir()
for uid in (0,1000,1001,65534):
 d=fixture/f'owner-{uid}';d.mkdir();(d/'file').write_text('original\n')
 os.chown(d,uid,uid);os.chown(d/'file',uid,uid)
stage=Path(tempfile.mkdtemp(prefix='steam-poc-stage-',dir='/tmp'));stage.chmod(0o755)
mounts=[]
original_ref=Path('/storage/games-internal/roms/steam/steam-runtime-steamrt-arm64/steamrt3c_platform_3c.0.20260729.253765/files/.ref')
disposable_ref=source/'runtime.ref'
disposable_ref.write_bytes(original_ref.read_bytes())
disposable_ref.chmod(0o600);os.chown(disposable_ref,65534,65534)
class Runtime(module['Runtime']):
 def command(self,name,*args):
  if name=='lxc-start':
   for label,src,opts in [('fixture',fixture,'bind'),('runtime',Path('/storage/games-internal/roms/steam/steam-runtime-steamrt-arm64'),'bind,ro')]:
    dest=stage/label;dest.mkdir()
    if label=='fixture':
     subprocess.run(super().command('mount','--bind','-o','X-mount.idmap=b:0:201000:1',src,dest),check=True)
    else:subprocess.run(super().command('mount','--bind','-o','X-mount.idmap=b:65534:201000:1',src,dest),check=True)
    mounts.append(dest)
    if label=='runtime':subprocess.run(['/usr/bin/mount','-o','remount,bind,ro,nosuid,nodev',str(dest)],check=True)
    with self.config.open('a') as f:f.write(f'lxc.mount.entry = {dest} opt/steam-poc-{label} none {opts},create=dir 0 0\n')
   dest=stage/'ref';dest.touch()
   subprocess.run(super().command('mount','--bind','-o','X-mount.idmap=b:65534:201000:1',disposable_ref,dest),check=True)
   mounts.append(dest)
   with self.config.open('a') as f:f.write(f'lxc.mount.entry = {dest} opt/steam-poc-runtime/steamrt3c_platform_3c.0.20260729.253765/files/.ref none bind,create=file 0 0\n')
  return super().command(name,*args)
r=Runtime(host/'host-tools',Path('/storage/rocknix-desktop/data/rootfs'),state=Path('/run/rocknix-lxc-steam-poc'))
def interrupted(*args):raise RuntimeError('interrupted')
signal.signal(signal.SIGTERM,interrupted)
result={}
try:
 subprocess.run(['systemctl','stop','rocknix-desktop.service'],check=True,timeout=60)
 if Path('/run/rocknix-lxc/resources.json').exists():raise RuntimeError('normal Desktop cleanup incomplete')
 r.start()
 code='''
from pathlib import Path
import os,json,subprocess
Path('/tmp/steam-poc-home').mkdir(exist_ok=True)
out={'uid':os.getuid(),'owners':{}}
for uid in (0,1000,1001,65534):
 p=Path('/opt/steam-poc-fixture')/f'owner-{uid}'
 row={'visible_uid':p.stat().st_uid}
 try:
  with (p/'file').open('a') as f:f.write('guest\\n');f.flush();os.fsync(f.fileno())
  q=p/'created';q.write_text('new');q.rename(p/'renamed');(p/'renamed').unlink()
  row['write']='ok'
 except OSError as e:row['write']=e.errno
 out['owners'][uid]=row
for name,args in {
 'nested':['unshare','--user','--map-root-user','--mount','--pid','--fork','sh','-ec','mount -t tmpfs tmpfs /tmp; echo nested-ok'],
 'requirements':['/opt/steam-poc-runtime/pressure-vessel/bin/steam-runtime-check-requirements'],
 'bwrap':['/opt/steam-poc-runtime/pressure-vessel/libexec/steam-runtime-tools-0/srt-bwrap','--unshare-user','--unshare-pid','--ro-bind','/','/','--proc','/proc','--dev','/dev','--tmpfs','/tmp','/bin/echo','bwrap-ok'],
 'bwrap_bindproc':['/opt/steam-poc-runtime/pressure-vessel/libexec/steam-runtime-tools-0/srt-bwrap','--unshare-user','--ro-bind','/','/','--ro-bind','/proc','/proc','--dev','/dev','--tmpfs','/tmp','/bin/echo','bindproc-ok'],
 'wrap_test':['/opt/steam-poc-runtime/pressure-vessel/bin/pressure-vessel-wrap','--test','--batch'],
 'runtime_true':['/opt/steam-poc-runtime/pressure-vessel/bin/pressure-vessel-wrap','--batch','--copy-runtime','--no-gc-runtimes','--no-generate-locales','--runtime=/opt/steam-poc-runtime/steamrt3c_platform_3c.0.20260729.253765','--variable-dir=/tmp/pv-stage1','--graphics-provider=','--','/usr/bin/true'],
}.items():
 try:
  p=subprocess.run(args,capture_output=True,text=True,timeout=120,env=dict(os.environ,HOME='/tmp/steam-poc-home',PRESSURE_VESSEL_ARCHITECTURES='aarch64-linux-gnu'));out[name]={'rc':p.returncode,'stdout':p.stdout[:4096],'stderr':p.stderr[:4096],'stderr_bytes':len(p.stderr.encode()),'cross_device_warnings':p.stderr.count('Invalid cross-device link')}
 except Exception as e:out[name]={'error':str(e)}
out['scratch_kib']=subprocess.run(['du','-sk','/tmp/pv-stage1'],capture_output=True,text=True).stdout
print(json.dumps(out))
'''
 p=r.attach('/usr/bin/setpriv','--reuid=1000','--regid=1000','--clear-groups','--','/usr/bin/python3','-',input=code,timeout=180)
 result['guest']={'rc':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
 result['backing']={str(uid):{'owner':(fixture/f'owner-{uid}').stat().st_uid,'content':(fixture/f'owner-{uid}'/'file').read_text()} for uid in (0,1000,1001,65534)}
finally:
 r.close()  # On failure retain evidence/resources; do not delete live mounts.
 for p in reversed(mounts):subprocess.run(['/usr/bin/umount',str(p)],check=True)
 shutil.rmtree(stage);shutil.rmtree(source)
print(json.dumps(result,indent=2))
