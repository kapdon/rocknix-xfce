#!/usr/bin/python3
"""Temporary RP6 experiment: request comes from the guest Apps menu."""
import json, os, select, subprocess, time
from pathlib import Path
BASE=Path('/tmp/desktop-handoff')
FIFO=Path('/run/rocknix-desktop/benchmark-control')
def call(*args, **kw):return subprocess.run(args,check=True,timeout=60,**kw)
def active(unit):return subprocess.run(['systemctl','is-active','--quiet',unit]).returncode==0
assert os.getuid()==0 and active('rocknix-desktop')
FIFO.unlink(missing_ok=True);os.mkfifo(FIFO,0o620);os.chown(FIFO,0,201000);os.chmod(FIFO,0o620)
fd=os.open(FIFO,os.O_RDWR|os.O_NONBLOCK)
if not select.select([fd],[],[],180)[0]:raise SystemExit('No menu request')
request=os.read(fd,128);os.close(fd)
if request!=b'satisfactory-baseline\n':raise SystemExit('Invalid menu request')
(BASE/'request.json').write_text(json.dumps({'request':request.decode().strip(),'desktop_active':active('rocknix-desktop'),'time':time.time()}))
FIFO.unlink(missing_ok=True)
samples=[]
try:
 call('systemctl','stop','rocknix-desktop.service')
 call('systemctl','stop','essway.service')
 assert not active('rocknix-desktop')
 call('systemd-run','--unit=desktop-handoff-game','--collect','--property=RuntimeMaxSec=240','--property=TimeoutStopSec=15','--property=KillMode=control-group','--property=TasksMax=1200','/bin/bash',str(BASE/'session.sh'),'--run-on-rp6-dev')
 for i in range(240):
  m={a.split(':')[0]:int(a.split()[1]) for a in Path('/proc/meminfo').read_text().splitlines() if a.startswith(('MemAvailable:','SwapFree:'))}
  m.update(elapsed=i,desktop_active=active('rocknix-desktop'))
  samples.append(m);(BASE/'memory.json').write_text(json.dumps(samples))
  if m['MemAvailable']<1536*1024 or not active('desktop-handoff-game'):break
  time.sleep(1)
finally:
 subprocess.run(['systemctl','stop','desktop-handoff-game.service'],timeout=30)
 call('systemctl','start','essway.service')
 call('systemctl','start','rocknix-desktop.service')
