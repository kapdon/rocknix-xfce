# Temporary experiment inserted before the installed runtime's main entrypoint.
_original_command = Runtime.command
_extra_stages = ('steam-test-registry', 'steam-test-runtime', 'steam-test-ref')
_recovery_globals = DESKTOP['DesktopMounts'].recover.__globals__
_recovery_globals['STAGES'] = (*_recovery_globals['STAGES'], *_extra_stages)
def _steam_test_command(self, name, *args):
    if name == 'lxc-start' and self.desktop is not None:
        if subprocess.run(['systemctl','is-active','--quiet','steam-bigpicture.scope']).returncode == 0:
            raise RuntimeError('native Steam is active')
        client = Path('/storage/games-internal/roms/steam')
        runtime = client / 'steam-runtime-steamrt-arm64'
        ref = 'steamrt3c_platform_3c.0.20260729.253765/files/.ref'
        specs = [('/storage/.steam','steam-test-registry','storage/.steam',0,False),
                 (runtime,'steam-test-runtime','storage/games-internal/roms/steam/steam-runtime-steamrt-arm64',65534,True),
                 (runtime/ref,'steam-test-ref','storage/games-internal/roms/steam/steam-runtime-steamrt-arm64/'+ref,65534,False)]
        for src, label, target, owner, readonly in specs:
            dest = self.desktop.directory / label
            isdir = Path(src).is_dir()
            if isdir: dest.mkdir(mode=0o755)
            else: dest.touch(mode=0o600)
            subprocess.run(self.desktop.tool('mount','--bind','-o',f'X-mount.idmap=b:{owner}:201000:1',src,dest),check=True)
            self.desktop.bound.append(dest)
            if readonly:
                subprocess.run(['/usr/bin/mount','-o','remount,bind,ro,nosuid,nodev',str(dest)],check=True)
            options = 'bind,create=' + ('dir' if isdir else 'file') + (',ro' if readonly else '')
            with self.config.open('a') as stream:
                stream.write(f'lxc.mount.entry = {dest} {target} none {options} 0 0\n')
    return _original_command(self,name,*args)
Runtime.command = _steam_test_command
