# Building ROCKNIX Desktop

Local, development and versioned builds use the [component build path](components.md),
resolving reusable compressed artifacts before Docker setup. `build-rootfs.sh`
is a convenience entry point to that same builder.

Build from a clean, committed checkout with Docker Buildx and `fakeroot` for
non-root archive packaging. Local AMD64 hosts can build the ARM64 target.
The private Firefox FFmpeg and keyboard builds use an ARM64 cross-compiler
on the build platform. Docker's QEMU/binfmt support runs ARM64 image stages
when needed.
The native ARM64 Trash package build retains Debian rules and skips upstream
suites by default. Clear the Docker build argument `DEB_BUILD_OPTIONS` when
changing those packages to run their suites; emulation has ptrace limitations.
GVfs rules defer runtime tests to autopkgtest, so package compilation alone is
not a GVfs runtime-test pass. A cross-host build can set `ROCKNIX_TRASH_PACKAGES_DIR`
to a complete audited artifact directory from a validated native ARM64 run.

From the repository root:

```sh
bash tests/check.sh
bash build-rootfs.sh
python3 scripts/build-components.py --plan
```

On an AMD64 host, supply the complete unchanged native Trash package artifact
directory while using the ordinary local Docker builder:

```sh
ROCKNIX_TRASH_PACKAGES_DIR=/path/to/native/trash-packages bash build-rootfs.sh
```

The manifest is `dist/components/release.json`; compressed artifacts and bindings
are in `build/component-store/`. See [assembly commands](components.md#local-commands).
The historical `dist/rocknix-desktop-rp6-arm64.tar.xz` export is no longer produced
by local or release builds and is not accepted as an update candidate.
For local update tests, assemble the manifest, then use its `upgrade.sh` with
`--bundle MANIFEST --sha256 HASH --check` before `--yes`. Never extract over a
running installation. Ordinary users should use the [download installer](../README.md#install-or-update).

Build inputs are defined in [Dockerfile.rootfs](../Dockerfile.rootfs),
[host tools](../build-support/lxc/Dockerfile.host-tools),
[Trash packages](../build-support/trash/README.md),
[Fuzzel](../build-support/fuzzel/README.md),
[wvkbd](../build-support/wvkbd/README.md) and
[Firefox FFmpeg](../build-support/ffmpeg/README.md).
MPV uses a [patched stock FFmpeg codec library](../build-support/mpv-ffmpeg/README.md)
to reset on seek, start Iris capture after header parsing, handle source changes
and recycle empty notifications.
It retains Debian's standard codec
configuration; the other FFmpeg libraries remain package-managed. Firefox selects a separate,
minimal H.264/AAC library build only for its own process and children. Its
source archive is checksum-pinned; the archive and build recipe ship with the
runtime. Test affected graphics and media behavior on the RP6.
Source archives, patches and required licenses ship with the corresponding
artifacts. Review distribution obligations when changing dependencies.

Upstream suites are not a default build gate. Run them when relevant source
changes or explicit requirements call for them, and record which checks ran.
Keep the existing artifact and source checks. Run GLib tests when changing
its mount-aware source patch. Test affected runtime behavior
on the RP6 using the local bundle.


## Xwayland dependencies

The guest image builds checksum-pinned Xwayland Satellite 0.8.3 with its locked
Rust dependencies. Its upstream source, vendored dependency sources and license
ship under `/opt/rocknix-xwayland`. Debian supplies Xwayland and X11 utilities.
The bridge ships as its own component; Debian X11 packages ship in the guest
base. Updates replace the guest system, so no offline X11 package transaction
is required.
