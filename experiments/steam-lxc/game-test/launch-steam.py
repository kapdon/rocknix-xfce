# Supervised RP6 experiment only; see ../GAME-TEST.md for prerequisites/recovery.
import sys
if sys.argv[1:] != ['--run-on-rp6-dev']:
    raise SystemExit('requires --run-on-rp6-dev and prepared disposable RP6 LXC')
from pathlib import Path
import runpy,subprocess,json
m=runpy.run_path('/storage/rocknix-desktop/managed/host/bin/rocknix-lxc')
r=m['Runtime'](Path('/storage/rocknix-desktop/managed/host/host-tools'),Path('/storage/rocknix-desktop/data/rootfs'),recovery_only=True)
(Path('/sys/fs/cgroup/unified/rocknix-lxc')/'memory.max').write_text(str(8*1024**3))
for args in [('/bin/chown','1000:1000','/storage'),('/bin/mkdir','-p','/tmp/steam-lxc-pv','/tmp/steam-lxc-logs'),('/bin/chown','1000:1000','/tmp/steam-lxc-pv','/tmp/steam-lxc-logs')]:
 p=r.attach(*args);assert p.returncode==0,p.stderr
env={'HOME':'/storage','USER':'rocknix','LOGNAME':'rocknix','DISPLAY':':0','XDG_RUNTIME_DIR':'/run/rocknix-session','WAYLAND_DISPLAY':'wayland-1','PULSE_SERVER':'unix:/run/rocknix-bridge/pulse','XDG_CONFIG_HOME':'/storage/.config','XDG_CACHE_HOME':'/storage/.cache','XDG_DATA_HOME':'/storage/.local/share','VK_DRIVER_FILES':'/run/rocknix-native/vulkan.json','LD_LIBRARY_PATH':'/run/rocknix-native/lib:/storage/.local/share/Steam/lib/aarch64-linux-gnu','PRESSURE_VESSEL_VARIABLE_DIR':'/tmp/steam-lxc-pv','STEAM_COMPAT_GRAPHICS_PROVIDER':'/storage/.local/share/fex-emu/RootFS/ArchLinux/graphics_provider.json','FEX_ROOTFS':'/run/rocknix-fex/ArchLinux','PROTON_LOG':'1','PROTON_LOG_DIR':'/tmp/steam-lxc-logs','MESA_LOADER_DRIVER_OVERRIDE':'msm','GALLIUM_DRIVER':'freedreno'}
args=['/bin/systemd-run','--unit=steam-lxc-test','--uid=1000','--gid=1000','--property=KillMode=control-group','--property=TasksMax=1200','--property=TimeoutStopSec=20','--working-directory=/storage']
args += ['--setenv='+k+'='+v for k,v in env.items()]
args += ['/usr/bin/dbus-run-session','--','/storage/.local/share/Steam/steamrtarm64/steam','-deckard','-steamos3','-gamepadui','-noshaders','-applaunch','526870']
r.attach('/bin/systemctl','stop','steam-lxc-test',timeout=35)
r.attach('/bin/systemctl','reset-failed','steam-lxc-test')
p=r.attach(*args);print('launch rc',p.returncode,p.stdout,p.stderr)
