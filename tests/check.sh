#!/bin/bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
python3 tests/docs.py
python3 tests/device-profile.py
python3 tests/install-power.py
bash tests/install-power.sh
python3 tests/audio-boundary.py
python3 tests/container-health.py
python3 tests/trash-packaging.py
python3 tests/trash-policy.py
python3 tests/trash-update.py
python3 tests/lxc-access.py
python3 tests/lxc-network.py
python3 tests/lxc-runtime.py
python3 tests/lxc-desktop.py
python3 tests/lxc-update.py
python3 tests/lxc-upgrade.py
python3 tests/lxc-bootstrap.py
python3 tests/lxc-maintenance-idle.py
python3 tests/lxc-password.py
python3 tests/lxc-hostname.py
python3 tests/lxc-session.py
python3 tests/keyboard-suppression.py
python3 tests/launcher-cleanup.py
python3 tests/settings-label.py
python3 tests/games.py
python3 tests/display-policy.py
python3 tests/display-host.py
python3 tests/display-metrics.py
python3 tests/display-menu.py
python3 tests/fuzzel-artifact.py
bash tests/storage-links.sh
fakeroot -- python3 tests/lxc-storage.py
fakeroot -- python3 tests/lxc-uninstall.py
fakeroot -- python3 tests/lxc-install.py
fakeroot -- python3 tests/install-state.py
fakeroot -- python3 tests/install-replace.py
fakeroot -- python3 tests/updater-helper-path.py
python3 tests/desktop-paths.py
bash tests/installer-layout.sh

while IFS= read -r file; do
  [ -f "$file" ] || continue
  if head -n 1 "$file" | grep -Eq '^#!.*/(bash|sh)$'; then
    bash -n "$file"
  fi
done < <(git ls-files --cached --others --exclude-standard)
python3 - <<'PY'
import ast
from pathlib import Path
paths = list(Path('rootfs-overlay/usr/local/bin').iterdir())
paths.append(Path('tests/firefox-marionette.py'))
paths.extend(Path('payload/bin').iterdir())
paths.extend(Path('build-support').rglob('*.py'))
paths.extend(Path('scripts').glob('*.py'))
paths.extend(Path('tests/device').glob('*.py'))
for path in paths:
    if path.is_file() and path.read_text().splitlines()[0] in ('#!/usr/bin/python3', '#!/usr/bin/env python3'):
        ast.parse(path.read_text(), filename=str(path))
PY

# Source only: no device checks, downloads, or system mutations are executed.
source ./install.sh
test_dir=$(mktemp -d)
trap 'rm -rf -- "$test_dir"' EXIT
printf 'test payload\n' >"$test_dir/$ASSET"
(cd "$test_dir" && sha256sum "$ASSET" >"$ASSET.sha256")
verify_bundle "$test_dir"
printf 'corruption\n' >>"$test_dir/$ASSET"
if (verify_bundle "$test_dir") >/dev/null 2>&1; then
  printf 'FAIL: corrupt payload accepted\n' >&2; exit 1
fi
printf 'invalid checksum\n' >"$test_dir/$ASSET.sha256"
if (verify_bundle "$test_dir") >/dev/null 2>&1; then
  printf 'FAIL: malformed checksum accepted\n' >&2; exit 1
fi
bash install.sh --help >/dev/null
bash uninstall.sh --help >/dev/null
if bash uninstall.sh --invalid >/dev/null 2>&1; then
  printf 'FAIL: unknown uninstall argument accepted\n' >&2; exit 1
fi
if bash install.sh --invalid >/dev/null 2>&1; then
  printf 'FAIL: unknown argument accepted\n' >&2; exit 1
fi
test "$VERSION" = latest
test "$ASSET" = rocknix-desktop-rp6-arm64.tar.xz
grep -q 'dist/rocknix-desktop-rp6-arm64.tar.xz' docs/build.md
grep -q 'button: LeftStick' payload/input/desktop.yaml
grep -q 'bindsym XF86Tools' payload/bin/launch-sway-desktop
grep -q 'bindsym F13' payload/bin/launch-sway-desktop
grep -q 'systemctl stop essway.service' payload/bin/launch-sway-desktop
if grep -q 'systemctl stop sway.service' payload/bin/launch-sway-desktop; then
  printf 'FAIL: Sway compositor would be stopped\n' >&2; exit 1
fi
grep -q 'rocknix-keyboard-toggle' rootfs-overlay/etc/xdg/waybar/config.jsonc
grep -q 'keyboard-control' payload/bin/rocknix-keyboard-toggle
grep -q 'kill -34' rootfs-overlay/usr/local/bin/rocknix-sway-session
grep -q 'systemctl start --no-block "${unit}"' payload/bin/restore-emulationstation
if grep -q '^systemctl start sway.service$' payload/bin/restore-emulationstation; then
  printf 'FAIL: synchronous Sway recovery can deadlock in ExecStopPost\n' >&2; exit 1
fi
grep -q '^TimeoutStopSec=45$' payload/systemd/rocknix-desktop.service
grep -q '^SuccessExitStatus=143$' payload/systemd/rocknix-desktop.service
grep -q 'rm -f -- "${CONTROL_FIFO}"' payload/bin/launch-sway-desktop
grep -q '/usr/share/applications/firefox-esr.desktop' Dockerfile.rootfs
grep -q '/usr/share/applications/foot-server.desktop' Dockerfile.rootfs
grep -q '/usr/share/applications/footclient.desktop' Dockerfile.rootfs
grep -q '^execute=Return KP_Enter$' rootfs-overlay/etc/xdg/fuzzel/fuzzel.ini
grep -q '^cancel=Escape$' rootfs-overlay/etc/xdg/fuzzel/fuzzel.ini
grep -q '^radius=0$' rootfs-overlay/etc/xdg/fuzzel/fuzzel.ini
grep -q '^dpi-aware=no$' rootfs-overlay/etc/xdg/fuzzel/fuzzel.ini
grep -q -- '--dpi-aware=no' rootfs-overlay/usr/local/bin/rocknix-launcher
if grep -q '^execute=.*space' rootfs-overlay/etc/xdg/fuzzel/fuzzel.ini; then
  printf 'FAIL: Fuzzel consumes Space instead of allowing multiword search\n' >&2; exit 1
fi
grep -q 'keyboard: KeyF14' payload/input/desktop.yaml
grep -q 'keyboard: KeyEnter' payload/input/desktop.yaml
grep -q 'keyboard: KeyEsc' payload/input/desktop.yaml
grep -q 'bindsym --no-repeat F14 exec env' payload/bin/launch-sway-desktop
grep -q 'button: RightStick' payload/input/desktop.yaml
grep -q 'keyboard: KeyF15' payload/input/desktop.yaml
grep -Fq 'bindsym --no-repeat F15 exec env' payload/bin/launch-sway-desktop
grep -q 'unbindsym F15' payload/bin/launch-sway-desktop
grep -q 'unbindsym F15' payload/bin/restore-emulationstation
grep -Fq 'XF86Tools|F13|F14|F15' payload/bin/preflight
grep -q "hide_edge_borders --i3 smart" payload/bin/launch-sway-desktop
grep -q 'DISPLAY_DIAGONAL_TENTHS=55' payload/bin/launch-sway-desktop
if grep -q 'custom/browser' rootfs-overlay/etc/xdg/waybar/config.jsonc; then
  printf 'FAIL: dedicated browser shortcut remains in Waybar\n' >&2; exit 1
fi
grep -q '2fe08f3bd52c6e795df8353d29deb89596b5099d' Dockerfile.rootfs
grep -q 'i64 = 32' build-support/ffmpeg/build.sh
grep -q 'BindsTo=sway.service' payload/systemd/rocknix-desktop.service
grep -q '^source /etc/profile$' payload/bin/preflight
grep -q 'INPUT_STATE_PRESENT=1' payload/bin/restore-emulationstation
grep -q 'ROCKNIX_SWAY_RUNTIME=1' rootfs-overlay/etc/rocknix-desktop-release
grep -q -- '--iidfile' build-rootfs.sh
python3 -m json.tool rootfs-overlay/etc/xdg/waybar/config.jsonc >/dev/null
if rg -q '%-' rootfs-overlay/etc/xdg/waybar/config.jsonc; then
  printf 'FAIL: Waybar chrono format contains an unsupported modifier\n' >&2; exit 1
fi
printf 'PASS: syntax, checksum rejection, lifecycle, shell and release checks\n'
grep -q 'dev/install.sh' README.md
bash tests/persistence.sh
bash tests/upgrade.sh
bash tests/release-selection.sh
bash tests/release-publication.sh
bash tests/installer-flow.sh
python3 tests/installer-command.py
python3 tests/session-lifecycle.py
python3 tests/return-confirmation.py
python3 tests/launcher-cache.py
python3 tests/window-close.py
python3 tests/window-policy.py

python3 tests/controller-fields.py
python3 tests/tools-metadata.py
python3 tests/keyboard-layout.py
python3 tests/helper-sandbox.py
python3 tests/package-rootfs.py
python3 tests/network-helper.py
