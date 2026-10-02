# Local component build validation — 2026-10-02

Implemented on `codex/component-builds`, based on the local cache fix
`7476ca8ec156460e638f5ab1d13faa3792c4ab57` above `dev` revision
`c1a1aec8e89b6ddeef3c9b78e58b132be5805599`. Nothing was pushed, merged,
published or dispatched to GitHub Actions during this validation.

## Measured build reuse

Benchmark source: `07467c1eeb15ac582ad84e0acf4fca9fe9af8ed4`.
Ubuntu 24.04 amd64 container on the same Ryzen 9800X3D host used for the earlier
packaging baseline, limited to four CPUs (cpuset 0–3) and 16 GiB RAM.
Python 3.12.3 and XZ 5.4.5. No compression preset or environment override.
Networking was disabled and no Docker socket was exposed to the benchmark.

The benchmark uses real compressed ARM64 components from a completed local build.
It first verifies the populated store, then times the actual resolver/build
function. Each CSS trial changes a disposable copy of the real Waybar stylesheet
with a unique comment. No working-tree source file is modified.

| Core resolve/build case | Trial 1 | Trial 2 | Trial 3 | Median |
| --- | ---: | ---: | ---: | ---: |
| Unchanged, populated local store | 0.340 s | 0.353 s | 0.339 s | 0.340 s |
| CSS edit, populated local store | 0.358 s | 0.374 s | 0.342 s | 0.358 s |

Every unchanged trial reused all ten components and ran no producer. Each CSS
trial reused nine components and built only `guest-integration`: one 112,640-byte
(110 KiB) tar input compressed to 17,460 bytes. Compression/packing for that
component took 0.017–0.019 seconds. There were no Docker invocations, rootfs
exports, native package rebuilds or large archive compression in any trial.

The prior full-package measurement at `7476ca8`, using Ubuntu 24.04, four CPUs,
16 GiB and the same compression defaults, was **453.089 seconds** (7m33s), of which
447.635 seconds was final tar/XZ. That is a packaging-stage comparison: the new
architecture avoids producing the full rootfs archive for a configuration edit.
It is not an end-to-end GitHub speedup or a cold-build comparison. The local store
and filesystem cache are warm; GitHub queueing, checkout, APT setup, tests,
metadata requests, cache transport and publication are outside these timings.
A fresh-runner fixture separately verifies that reused remote components resolve
from small descriptors without downloading large archives.

Reproduce after seeding a real local component store:

```sh
python3 scripts/benchmark-components.py --samples 3
```

Keep the same native-package override environment used for the seed build.
Use Ubuntu 24.04 with `--cpus 4 --cpuset-cpus 0-3 --memory 16g --network none`,
mount the checkout/store and any native package inputs, and run the command above
without exposing Docker. The harness fails if any compiled component is missing
or a trial attempts to invoke Docker. Results default to
`dist/component-benchmark/results.json`; this run used `dist/runner-profile/`.

## Real payload composition

All ten components were built from actual Docker outputs or repository inputs.
The existing audited native ARM64 Trash package directory was reused on this
amd64 host. Its bytes have distinct local input keys and the resulting manifest
is marked `local_override`; the publisher explicitly refuses it. Native Trash
compilation and real GitHub publication were not exercised by this trial.

The complete fresh-install and retained-update profiles assembled successfully
under one fakeroot session at component implementation revision
`cb02f8df2edb0653a93acdcfaca65cdccf0e47be`. Later benchmark/documentation and
release-note wording changes do not alter those component input keys.
Manifest SHA-256:
`54cc83b975ab63ebe5ea49f828e1d7e3df07c15616713bf6cbfd824faaeb6bcf`.

Verified against the real artifacts:

- Both profiles contain the complete 292-file managed integration union.
- Fresh install contains nine components, including the Debian base; the
  standalone package transaction is omitted because its packages are in the base.
- Update contains nine components, including the package transaction; the Debian
  base, account database and package database are excluded.
- Guest home UID/GID 1000, guest sudo and host newuidmap mode 4755, and guest
  `/tmp` mode 1777 survive assembly. Ownership checks ran inside fakeroot.
- LXC, Fuzzel and the keyboard binary have ARM64 ELF headers.
- Guest APT sources point to normal Debian/security repositories after the build;
  the snapshot freshness override is absent from the installed guest.
- Composition preserves Unicode paths, symlinks, hardlinks and the managed
  namespace boundary. Debian default configuration is omitted from the base
  wherever integration owns that path, preventing overlapping payloads.

Assembly took 39.383 seconds for install and 15.501 seconds for update on the
unconstrained local host. These are validation observations, not device or CI
performance claims. The assembled loose directories are test staging output;
fakeroot ownership does not persist outside that session.

## Automated checks and remaining acceptance

`bash tests/check.sh` passed, including legacy installer/update coverage and the
new component and publication cases. Component and publication tests also passed
inside Ubuntu's Python 3.12 environment. The tests cover selective invalidation,
base-only reuse of the audited Trash transaction, immutable publication ordering,
collision/failure handling, full managed-file union, v1/v2 installer dispatch,
and checksum, ownership and archive path/link rejection.

The first implementation optimizes build reuse. Device updates still stage the
complete non-base set; changed-only device transfer and installed-component
receipts are not implemented. Existing retained-rootfs, package transaction,
local-edit and recovery behavior remains the update mechanism.

Native ARM64 hosted timing and component publication were subsequently checked
in the [GitHub benchmark](components-github-benchmark.md). Development-channel
promotion, RP6 fresh install, retained update and interruption recovery remain
acceptance work before production use. No hardware validation is claimed by
these local checks.
