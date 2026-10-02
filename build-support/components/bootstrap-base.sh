#!/bin/sh
# Stable fresh-install initialization. Never run this during a retained update.
set -eu
useradd --create-home --uid 1000 --shell /bin/bash --groups sudo rocknix
passwd --lock root
python3 /tmp/rocknix-default-password
rm -f /tmp/rocknix-default-password /usr/sbin/policy-rc.d
systemctl set-default multi-user.target
systemctl enable rocknix-desktop-session.service
systemctl mask getty.target console-getty.service NetworkManager.service \
  NetworkManager-wait-online.service systemd-networkd.service \
  systemd-networkd.socket systemd-networkd-wait-online.service \
  sys-kernel-config.mount sys-kernel-debug.mount systemd-firstboot.service
mkdir -p /home/rocknix-default/Desktop /home/rocknix-default/.config /run \
  /storage/Desktop /storage/Steam /storage/backup /storage/games-external /storage/games-internal
chmod 1777 /tmp
rm -f /etc/machine-id /var/lib/dbus/machine-id
apt-get clean
rm -rf /var/lib/apt/lists/*
dpkg-query -W -f='${binary:Package}\t${Version}\n' | sort > /etc/rocknix-desktop-packages.tsv
# Freeze build resolution, not the installed user's future security updates.
sed -i 's|http://snapshot.debian.org/archive/debian-security/[0-9TZ]*/|https://deb.debian.org/debian-security|g; s|http://snapshot.debian.org/archive/debian/[0-9TZ]*/|https://deb.debian.org/debian|g' /etc/apt/sources.list.d/debian.sources
rm -f /etc/apt/apt.conf.d/99snapshot
