#!/bin/bash
# Run as root or under one fakeroot session. Keep extraction, modifications and
# repacking in that same session so image UID/GID and setuid metadata survive.
set -Eeuo pipefail
[ "$(id -u)" = 0 ] || { printf 'Packaging requires root or fakeroot\n' >&2; exit 1; }
CONTAINER_ID=$1
PROJECT_DIR=$2
TEMP_DIR=$3
IMAGE_ID=$4
REVISION=$5
OUTPUT=$6
HOST_CONTAINER_ID=${7:?trusted host-tools container is required}
TRASH_PACKAGES_DIR=${8:?audited Debian package artifacts are required}

docker export "${CONTAINER_ID}" | tar --numeric-owner --same-owner -x -C "${TEMP_DIR}/rootfs"
# The staging root may have been created before fakeroot started. Normalize
# only that directory; preserve every Debian service-account owner below it.
chown 0:0 "${TEMP_DIR}/rootfs"
rm -f "${TEMP_DIR}/rootfs/etc/resolv.conf" "${TEMP_DIR}/rootfs/.dockerenv"
: >"${TEMP_DIR}/rootfs/etc/resolv.conf"
printf 'rocknix-desktop\n' >"${TEMP_DIR}/rootfs/etc/hostname"
printf '127.0.0.1 localhost\n127.0.1.1 rocknix-desktop\n::1 localhost ip6-localhost ip6-loopback\n' >"${TEMP_DIR}/rootfs/etc/hosts"
for directory in dev proc run sys tmp; do
  find "${TEMP_DIR}/rootfs/${directory}" -mindepth 1 -delete
done
chmod 1777 "${TEMP_DIR}/rootfs/tmp"

for required in \
  usr/bin/mount usr/bin/dbus-run-session \
  usr/bin/firefox-esr usr/bin/foot usr/bin/fuzzel usr/bin/glmark2-wayland usr/bin/waybar \
  usr/local/bin/wvkbd-rocknix usr/local/bin/rocknix-launcher usr/local/bin/rocknix-status \
  usr/local/bin/rocknix-window-switcher usr/local/bin/rocknix-sway-session \
  usr/bin/Xwayland usr/bin/xdpyinfo opt/rocknix-xwayland/bin/xwayland-satellite \
  opt/ffmpeg-rpi-7.1.5/bin/ffmpeg; do
  [ -x "${TEMP_DIR}/rootfs/${required}" ] || {
    printf 'Built rootfs is missing %s\n' "${required}" >&2; exit 1;
  }
done
[ ! -e "${TEMP_DIR}/rootfs/usr/bin/Xorg" ]
grep -qx 'ROCKNIX_SWAY_RUNTIME=1' "${TEMP_DIR}/rootfs/etc/rocknix-desktop-release"
grep -qx 'ROCKNIX_LXC_RUNTIME=1' "${TEMP_DIR}/rootfs/etc/rocknix-desktop-release"

mkdir "${TEMP_DIR}/host-tools"
docker export "${HOST_CONTAINER_ID}" | tar --numeric-owner --same-owner -x -C "${TEMP_DIR}/host-tools"
chown 0:0 "${TEMP_DIR}/host-tools"
for required in lxc-start lxc-stop lxc-info lxc-attach slirp4netns mount setfacl getfacl \
  bwrap dbus-run-session xdg-dbus-proxy nm-connection-editor; do
  [ -x "${TEMP_DIR}/host-tools/usr/bin/${required}" ] || {
    printf 'Trusted host tools missing %s\n' "$required" >&2; exit 1;
  }
done
for directory in storage home/rocknix-default; do
  [ -d "${TEMP_DIR}/host-tools/${directory}" ] && \
    [ ! -L "${TEMP_DIR}/host-tools/${directory}" ] || {
    printf 'Trusted host tools missing real sandbox directory %s\n' "$directory" >&2; exit 1;
  }
done
rm -f "${TEMP_DIR}/host-tools/.dockerenv"

# Do not silently ship the isolated editor with GTK fallback styling, or with
# stale theme assets from a differently built trusted image.
for asset in etc/gtk-3.0/settings.ini usr/share/themes/ROCKNIX/index.theme \
  usr/share/themes/ROCKNIX/gtk-3.0/gtk.css; do
  cmp -s "${PROJECT_DIR}/rootfs-overlay/${asset}" "${TEMP_DIR}/host-tools/${asset}" || {
    printf 'Trusted network theme missing or stale: %s\n' "$asset" >&2; exit 1;
  }
done

mkdir "${TEMP_DIR}/payload"
tar --exclude=__pycache__ -cf - -C "${PROJECT_DIR}/payload" . | \
  tar -xf - -C "${TEMP_DIR}/payload"
for file in install-device.sh install.sh README.md uninstall.sh upgrade.sh; do
  cp -a "${PROJECT_DIR}/${file}" "${TEMP_DIR}/${file}"
  chown 0:0 "${TEMP_DIR}/${file}"
done
# These are project-managed host executables/config, not service-owned Debian
# files. Normalize only this payload, never blanket-chown the exported rootfs.
chown -R 0:0 "${TEMP_DIR}/payload"
chmod 0755 "${TEMP_DIR}/install-device.sh"
cp "${PROJECT_DIR}/payload/bin/rocknix-lxc-upgrade" "${TEMP_DIR}/upgrade-lxc.py"
chown 0:0 "${TEMP_DIR}/upgrade-lxc.py"
cp "${PROJECT_DIR}/rootfs-overlay/usr/local/bin/rocknix-container-update" \
  "${TEMP_DIR}/payload/guest/rocknix-container-update"
chown 0:0 "${TEMP_DIR}/payload/guest/rocknix-container-update"
python3 "${PROJECT_DIR}/scripts/package-trash.py" "${TRASH_PACKAGES_DIR}" \
  "${TEMP_DIR}/payload/guest/trash-packages.tar"
chown 0:0 "${TEMP_DIR}/payload/guest/trash-packages.tar"

printf 'built=%s\nbase_image=%s\nrootfs_image=%s\narchitecture=arm64\ncommit=%s\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  'debian@sha256:a99cfc517144bc59b1978475ec53b46ecabec7e43635402ee5b77cc54cd1b20a' \
  "${IMAGE_ID}" "${REVISION}" >"${TEMP_DIR}/build-info"
if [ -f "${TEMP_DIR}/host-tools-image-id" ]; then
  printf 'host_tools_image=%s\n' "$(cat "${TEMP_DIR}/host-tools-image-id")" >> "${TEMP_DIR}/build-info"
fi
cp "${TEMP_DIR}/build-info" "${TEMP_DIR}/rootfs/etc/rocknix-desktop-build-info"
chown 0:0 "${TEMP_DIR}/build-info" "${TEMP_DIR}/rootfs/etc/rocknix-desktop-build-info"
python3 "${PROJECT_DIR}/scripts/package-integration.py" \
  "${TEMP_DIR}/rootfs" "${TEMP_DIR}/desktop-integration.tar.gz"
# Export the install/update contract; exclude build scratch and artifacts.
tar --numeric-owner -cJf "${OUTPUT}" -C "${TEMP_DIR}" \
  ./rootfs ./host-tools ./payload ./install-device.sh ./install.sh ./README.md \
  ./uninstall.sh ./upgrade.sh ./upgrade-lxc.py ./build-info \
  ./desktop-integration.tar.gz
