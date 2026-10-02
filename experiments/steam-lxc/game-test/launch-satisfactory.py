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
steam='/storage/.local/share/Steam'
env.update({'SteamAppId':'526870','SteamGameId':'526870','STEAM_COMPAT_APP_ID':'526870','STEAM_COMPAT_CLIENT_INSTALL_PATH':steam,'STEAM_COMPAT_DATA_PATH':steam+'/steamapps/compatdata/526870','STEAM_COMPAT_INSTALL_PATH':steam+'/steamapps/common/Satisfactory','STEAM_COMPAT_LIBRARY_PATHS':steam,'STEAM_COMPAT_SHADER_PATH':steam+'/steamapps/shadercache/526870'})
args=['/bin/systemd-run','--unit=satisfactory-lxc-test','--uid=1000','--gid=1000','--property=KillMode=control-group','--property=TasksMax=1200','--property=TimeoutStopSec=20','--working-directory='+env['STEAM_COMPAT_INSTALL_PATH']]
args += ['--setenv='+k+'='+v for k,v in env.items()]
args += [steam+'/steamapps/common/SteamLinuxRuntime_4-arm64/_v2-entry-point','--verb=waitforexitandrun','--',steam+'/steamapps/common/Proton 11.0 (ARM64)/proton','waitforexitandrun',steam+'/steamapps/common/Satisfactory/FactoryGameSteam.exe','-NO_EOS_OVERLAY']
r.attach('/bin/systemctl','stop','satisfactory-lxc-test',timeout=35)
r.attach('/bin/systemctl','reset-failed','satisfactory-lxc-test')
p=r.attach(*args);print('launch rc',p.returncode,p.stdout,p.stderr)
