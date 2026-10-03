# Building ROCKNIX Desktop

Development CI uses the [component build path](components.md), resolving reusable
compressed artifacts before Docker setup. The commands below also retain the
explicit monolithic/offline builder used by stable releases.

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
(cd dist && sha256sum -c rocknix-desktop-rp6-arm64.tar.xz.sha256)
```

On an AMD64 host, supply the complete unchanged native Trash package artifact
directory while using the ordinary local Docker builder:

```sh
ROCKNIX_TRASH_PACKAGES_DIR=/path/to/native/trash-packages bash build-rootfs.sh
```

The bundle is `dist/rocknix-desktop-rp6-arm64.tar.xz`. Inspect its `build-info` for
source commit, build time and image provenance. The builder exports independent
trusted host tools and a Debian runtime. This historical export is not accepted
by the updater. For local update testing, build components with
`python3 scripts/build-components.py`, assemble the manifest with
`payload/bin/rocknix-components`, and use the assembled `upgrade.sh` with
`--bundle dist/components/release.json --sha256 HASH --check` before `--yes`.
Never extract over a running installation. Ordinary
users should use the [download installer](../README.md#install-or-update).

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

The offline/stable builder also reuses BuildKit layers. The stable workflow restores/exports
separate ARM64 caches for Trash packages, Fuzzel, the runtime and trusted host
tools. The packaging build uses the same builder. Runtime package installation
and compiled dependencies live before the final
overlay stage. Changing a launcher, theme or adding overlay files reuses APT,
audited Trash packages, Fuzzel, keyboard and both codec dependency layers.
Changing dependency recipes, patches or package artifacts invalidates their
dependent layers as usual.

Fuzzel's toolchain, protocol generation and Pixman build are separate stages.
Changing its artifact checker or distributed recipe only rebuilds provenance
and validation; changing Fuzzel sources reuses protocol/Pixman builds. The
keyboard compiler copies only the consumed patches, customizer and symbols;
its support documentation is still distributed without triggering compilation.
Trash package versions are scoped after its toolchain stage and parallelism
is scoped to package compilation. Changing those arguments does not reinstall
the toolchain. The existing archive compression settings are retained.

An unchanged APT layer does not fetch new
security packages. Refresh dependencies deliberately with a fresh builder or
no-cache build using the same inputs, then validate locally and on hardware.
A cache miss performs a full build; cache availability is not a requirement.

The manually dispatched [Development components workflow](../.github/workflows/development.yml)
publishes reusable components and a rolling manifest. Each successful publication
summarizes the release highlights and links to the full changes since the latest
stable release in [CHANGELOG.md](../CHANGELOG.md). Benchmark runs publish only reusable
artifacts. Preserve the manifest, build logs and source metadata; cached checks
must identify their original execution rather than claim a new run. Verify
artifact checksums and source/image provenance before RP6 testing. Rolling publication is
restricted to `dev`; [versioned publication](../.github/workflows/release.yml)
also requires the exact current `dev` commit.

See [contributing and publication](../contributor.md). Local checks/builds do
not prove device behavior or GitHub delivery.

Remote-cache preparation loads the runtime and host-tools images into Docker.
A metadata-only cache hit can otherwise leave layers remote and unavailable to
later build calls that have no cache importer. Trash installation consumes a
stage containing only audited packages, source artifacts, checksums and build
logs; per-run exporter provenance remains in the original artifact directory
and does not invalidate installation. Archive compression settings are unchanged.
## Xwayland dependencies

The guest image builds checksum-pinned Xwayland Satellite 0.8.3 with its locked
Rust dependencies. Its upstream source, vendored dependency sources and license
ship under `/opt/rocknix-xwayland`. Debian supplies Xwayland and X11 utilities.
Both the full bundle and the Xwayland component retain signed-APT package artifacts for offline updates
of existing containers. Maintenance checks the package allowlist, keeps newer
installed versions and refuses removals or unrelated package changes.
