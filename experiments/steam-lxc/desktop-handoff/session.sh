#!/bin/bash
set -euo pipefail
# Supervised experiment; launch in the bounded unit documented in ../NATIVE-GAMESCOPE.md.
[ "${1:-}" = --run-on-rp6-dev ] || { echo 'Requires --run-on-rp6-dev'; exit 2; }
[ "$(id -u)" = 0 ] || exit 1
! systemctl is-active --quiet rocknix-desktop.service || exit 1
if systemctl is-active --quiet steam-bigpicture.scope; then
    echo 'Close native Gaming Mode Steam first'; exit 1
fi
[ -S /run/0-runtime-dir/wayland-1 ] || exit 1
source /etc/profile
export HOME=/storage USER=root LOGNAME=root
export XDG_RUNTIME_DIR=/run/0-runtime-dir WAYLAND_DISPLAY=wayland-1
export PULSE_SERVER=unix:/run/0-runtime-dir/pulse/native
export STEAM_COMPAT_GRAPHICS_PROVIDER=/storage/.local/share/fex-emu/RootFS/ArchLinux/graphics_provider.json
export DISABLE_LSFGVK=1
export ENABLE_GAMESCOPE_WSI=0
export MANGOHUD_CONFIG=fps,frametime,ram,vram,gpu_stats,cpu_stats,output_folder=/tmp/desktop-handoff,autostart_log=1,log_duration=240
unset DISPLAY MESA_LOADER_DRIVER_OVERRIDE VK_DRIVER_FILES VK_ICD_FILENAMES
original=()
for name in x86 box32 box64; do
    file=/proc/sys/fs/binfmt_misc/$name
    [ -f "$file" ] || continue
    read -r state < "$file"
    original+=("$name:$state")
    echo 0 > "$file"
done
cleanup() {
    for value in "${original[@]}"; do
        file=/proc/sys/fs/binfmt_misc/${value%%:*}
        [ -f "$file" ] || continue
        if [ "${value#*:}" = enabled ]; then echo 1 > "$file"; else echo 0 > "$file"; fi
    done
}
trap cleanup EXIT
LD_LIBRARY_PATH=/storage/.local/share/Steam/lib/aarch64-linux-gnu \
/usr/bin/gamescope --backend wayland -W 1280 -H 720 -w 1280 -h 720 -r 60 --mangoapp --xwayland-count 2 --force-windows-fullscreen -- \
/storage/.local/share/Steam/steamrtarm64/steam -deckard -steamos3 -nobigpicture -noshaders -silent -applaunch 526870
