#!/usr/bin/python3
"""Exercise the real packager with a tiny Docker-export fixture, without Docker."""
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile

PROJECT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="rocknix-package-test-") as temp:
    work = Path(temp)
    export = work / "export.tar"
    with tarfile.open(export, "w") as archive:
        def add(name, data=b"", mode=0o755, uid=0, gid=0, directory=False):
            item = tarfile.TarInfo(name)
            item.uid, item.gid, item.mode = uid, gid, mode
            item.type = tarfile.DIRTYPE if directory else tarfile.REGTYPE
            item.size = 0 if directory else len(data)
            archive.addfile(item, None if directory else io.BytesIO(data))
        for directory in ("dev", "proc", "run", "sys", "tmp", "etc", "var/lib/service", "storage", "home/rocknix-default"):
            add(directory, directory=True, uid=101 if directory == "var/lib/service" else 0)
        required = "bwrap setfacl getfacl mount dbus-run-session xdg-dbus-proxy nm-connection-editor lxc-start lxc-stop lxc-info lxc-attach slirp4netns firefox-esr foot fuzzel glmark2-wayland waybar Xwayland xdpyinfo".split()
        for name in required:
            add("usr/bin/" + name, b"fixture")
        for name in "wvkbd-rocknix rocknix-launcher rocknix-status rocknix-window-switcher rocknix-sway-session".split():
            add("usr/local/bin/" + name, b"fixture")
        add("opt/rocknix-xwayland/bin/xwayland-satellite", b"fixture")
        add("opt/rocknix-xwayland/packages/fixture.deb", b"fixture", 0o644)
        add("opt/ffmpeg-rpi-7.1.5/bin/ffmpeg", b"fixture")
        add("etc/rocknix-desktop-release", b"ROCKNIX_SWAY_RUNTIME=1\nROCKNIX_LXC_RUNTIME=1\n", 0o644)
        add("usr/bin/setuid-fixture", b"fixture", 0o4755)
        add("var/lib/service/data", b"service", 0o640, 101, 102)
        for asset in ('etc/gtk-3.0/settings.ini', 'usr/share/themes/ROCKNIX/index.theme',
                      'usr/share/themes/ROCKNIX/gtk-3.0/gtk.css'):
            add(asset, (PROJECT / 'rootfs-overlay' / asset).read_bytes(), 0o644)
    mock = work / "bin"
    mock.mkdir()
    docker = mock / "docker"
    docker.write_text('#!/bin/sh\n[ "$1" = export ] || exit 1\nexec cat "$EXPORT_FIXTURE"\n')
    docker.chmod(0o755)
    stage = work / "stage"
    (stage / "rootfs").mkdir(parents=True)
    output = work / "bundle.tar.xz"
    packages = work / 'packages'; packages.mkdir()
    (packages / 'fixture.deb').write_bytes(b'opaque package fixture')
    env = dict(os.environ, PATH=str(mock) + ":" + os.environ["PATH"], EXPORT_FIXTURE=str(export))
    subprocess.run(["fakeroot", "--", "bash", str(PROJECT / "scripts/package-rootfs.sh"),
                    "fixture", str(PROJECT), str(stage), "sha256:fixture", "test-revision", str(output), "host-fixture", str(packages)],
                   env=env, check=True)
    with tarfile.open(output) as archive:
        def metadata(name):
            item = archive.getmember("./" + name)
            return item.uid, item.gid, item.mode
        assert metadata("rootfs/usr/bin/setuid-fixture") == (0, 0, 0o4755)
        assert metadata("rootfs")[:2] == (0, 0)
        assert metadata("host-tools")[:2] == (0, 0)
        assert metadata("rootfs/var/lib/service/data") == (101, 102, 0o640)
        assert metadata("rootfs/tmp") == (0, 0, 0o1777)
        assert archive.extractfile('./rootfs/etc/hostname').read() == b'rocknix-desktop\n'
        assert b'127.0.1.1 rocknix-desktop\n' in archive.extractfile('./rootfs/etc/hosts').read()
        assert metadata("host-tools/usr/bin/lxc-start")[:2] == (0, 0)
        assert metadata("host-tools/storage")[:2] == (0, 0)
        assert metadata('payload/guest/trash-packages.tar')[:2] == (0, 0)
        with tarfile.open(fileobj=archive.extractfile('./payload/guest/trash-packages.tar')) as bundled:
            assert bundled.extractfile('fixture.deb').read() == b'opaque package fixture'
            assert bundled.getmember('install-image.py').isfile()
        for name in ("payload/bin/rocknix-helper-sandbox", "install-device.sh", "build-info", "rootfs/etc/rocknix-desktop-build-info"):
            assert metadata(name)[:2] == (0, 0), name
        managed = json.load(archive.extractfile('./rootfs/var/lib/rocknix-desktop/managed.json'))
        assert managed['format'] == 1
        assert 'usr/local/bin/wvkbd-rocknix' in managed['files']
        assert 'var/lib/service/data' not in managed['files']
        assert 'usr/bin/firefox-esr' not in managed['files']
        with tarfile.open(fileobj=io.BytesIO(archive.extractfile('./desktop-integration.tar.gz').read())) as integration:
            assert json.load(integration.extractfile('manifest.json')) == managed
            assert all(member.isfile() or member.issym() for member in integration.getmembers())
    # Missing mountpoints failed only on hardware before this packaging gate.
    incomplete = work / 'incomplete.tar'
    with tarfile.open(export) as source, tarfile.open(incomplete, 'w') as destination:
        for member in source.getmembers():
            if member.name != 'storage':
                destination.addfile(member, source.extractfile(member) if member.isfile() else None)
    broken_stage = work / 'broken-stage'
    (broken_stage / 'rootfs').mkdir(parents=True)
    result = subprocess.run(['fakeroot', '--', 'bash', str(PROJECT / 'scripts/package-rootfs.sh'),
        'fixture', str(PROJECT), str(broken_stage), 'sha256:fixture', 'test-revision',
        str(work / 'invalid.tar.xz'), 'host-fixture', str(packages)],
        env=dict(env, EXPORT_FIXTURE=str(incomplete)), capture_output=True, text=True)
    assert result.returncode != 0
    assert 'missing real sandbox directory storage' in result.stderr
    stale = work / 'stale-theme.tar'
    with tarfile.open(export) as source, tarfile.open(stale, 'w') as destination:
        for member in source.getmembers():
            if member.name != 'usr/share/themes/ROCKNIX/gtk-3.0/gtk.css':
                destination.addfile(member, source.extractfile(member) if member.isfile() else None)
    stale_stage = work / 'stale-stage'
    (stale_stage / 'rootfs').mkdir(parents=True)
    result = subprocess.run(['fakeroot', '--', 'bash', str(PROJECT / 'scripts/package-rootfs.sh'),
        'fixture', str(PROJECT), str(stale_stage), 'sha256:fixture', 'test-revision',
        str(work / 'stale.tar.xz'), 'host-fixture', str(packages)],
        env=dict(env, EXPORT_FIXTURE=str(stale)), capture_output=True, text=True)
    assert result.returncode != 0
    assert 'Trusted network theme missing or stale' in result.stderr
print("PASS: package preserves service ownership and setuid modes; host payload is root-owned")
