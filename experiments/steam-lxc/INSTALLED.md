# RP6 installed-state findings — 2026-10-02

**Later evidence:** [DEVICE-TESTS.md](DEVICE-TESTS.md) supersedes the stage-1
permission/pending-test statements below. The user authorized RP6 development;
disposable idmap and ARM64 nested-runtime tests have now run. Steam/client/game
and native round-trip qualification remain outstanding.

Read-only SSH inventory succeeded using existing local credentials and the
previously verified device connection. Credentials, addresses, raw inventory,
library account metadata and process details remain in private local artifacts.
No Steam, game, runtime checker or foreign loader was executed; no device files,
mounts, services or configuration were deliberately changed. Other work already
had Desktop applications running; this investigation left them alone. These are
point-in-time observations, not an atomic snapshot or end-to-end qualification.

## Installed revisions

- RP6 / SM8550 / AArch64: ROCKNIX nightly `20260930`, firmware build
  `9fd38fa87094d4f0e956d03ac6c660fe4fd5e9d6`.
- Installed Desktop build-info: source
  `222bbb47bbb6886bd98e4a3c274f05d628314023`, built `2026-10-02T14:34:18Z`.
  This is the separate host-library-reuse work, **not** this investigation's
  `c1a1aec` base. Xwayland and xwayland-satellite were already running.
- ARM64 runtime directory: `steamrt3c_platform_3c.0.20260729.253765`.
  Custom tools include `GE-Proton11-7-aarch64` and
  `proton-cachyos-11.0-20260703-slr-arm64`; names identify installed directories,
  not validated execution or complete content integrity.
- Client includes ARM64 and x86 branches. Cached package metadata includes the
  ARM64 beta revision `861407927dc8efb407da7cf`; this is not a full binary hash.

Installed launcher SHA256 (distinct from the pinned research checkout):

| Script | SHA256 |
| --- | --- |
| `start_steam.sh` | `077ed2e713683cd449c4007e40990326f9040a0fe177289eb6741f34e9467d05` |
| `start_steam_arm64.sh` | `e01b7b31b87b1f5bebab2d846317accfcec9a3ac1cfcf5e82f92a6d57834195c` |
| `start_steam_x86.sh` | `ececb7f4594129292814f6db7c44f164a23255a1d88fd94e57f4d37383a13b23` |

Inspection confirms shared-file preparation and ARM64 binfmt changes occur
before scope re-exec. Launch stops Sway for the DRM gamescope route. Therefore
the proposed gate must precede script entry, and these launchers remain unsuitable
as guest entrypoints. The installed scripts have no shared Desktop Steam lease.

## Actual storage

`/storage/Steam` is absent. `/storage/.local/share/Steam` points to
`/storage/games-internal/roms/steam`. The client root and `/storage/.steam` are
native UID/GID0, mode0755. `.steam` contains registry/settings and SDK/client
aliases as well as transient PID/pipe/token filenames; token contents were not
read. Treat persistent registry data separately from transient IPC.

The configured libraries are the client root and `/storage/roms/steam`.
Mountinfo shows `/storage/roms` is a bind of `games-external/roms` from the same
ext4 storage filesystem. Device/inode comparison confirms `/storage/roms/steam`
and `/storage/games-external/roms/steam` are the same directory. Preserve the
logical library path; avoid treating those aliases as independent copies.
This does not qualify future removable libraries or other filesystems.

The ArchLinux FEX root is native UID/GID1000 and remains a read-only reuse
candidate. Its graphics-provider JSON uses root `./`, with `/usr/lib` and
`/usr/lib32` architecture paths interpreted within that provider root. An exact
guest alias is preferable to importing host library directories globally.

## Mixed ownership changes the writable-reuse proposal

A bounded metadata scan of the client root completed 136,610 entries without
hitting its count/time limit. Selected groups are:

| Subtree / native owner | Entries | Directories | Implication |
| --- | ---: | ---: | --- |
| ARM64 downloaded runtime / 65534:65534 | 6,774 | 685 | Native root mapping alone does not grant guest1000 owner permissions. |
| `ubuntu12_32` / 65534:65534 | 5,551 | 562 | Same limitation for this x86 runtime content. |
| Custom compatibility tools / 1001:1001 | 7,886 | 878 | Separate foreign-owner content exists within the tools tree. |
| Custom compatibility tools / 0:0 | 11,564 | 853 | Even one top-level tools directory has multiple ownership groups. |
| `steamapps` / 0:0 | 74,922 | 8,676 | Root mapping is promising for these entries, not a proof of writable update behavior. |

Mode-bit checks found all 6,774 ARM runtime entries and 7,870 of the 1001-owned
tool entries lacked write permission for native UID/GID0 without capabilities.
Native root can bypass discretionary permissions; unprivileged guest1000 cannot
inherit that capability just by mapping ownership. ACLs were not collected, so
these are mode-based blockers to assuming write access, not a full access audit.
Read-only files with writable parents can sometimes be replaced; non-writable
foreign-owned directories still prevent general recursive update/cleanup.

Do **not** collapse owners, recursively chown/chmod, or map foreign owners onto
the same guest owner and claim metadata preservation. Per-subtree mounts may
permit selected writes but can prevent atomic directory replacement at mount
boundaries; they are not a universal updater fix.

Revised candidate: retain existing client, game data and all downloaded runtime
bytes; map root-owned mutable state, initially consume foreign-owned runtime
and tool content read-only, and perform their maintenance natively with Desktop
fully stopped. This maximizes content reuse but is only viable if client/runtime
launch and updates respect that policy. Steam auto-update behavior is an explicit
test gate. If it requires writable foreign-owned content, either a narrowly
designed separate writable runtime/client state is needed or native Steam stays
the execution route. Full shared writable updates are **not established**.

## Static ABI candidates

Device `readelf` uses tag names without GNU parentheses. The first regex-based
capture missed DT_NEEDED rows; those empty lists were discarded. The new
`elf_metadata.py` parser recognizes both formats and rejects unsupported/empty
dependency output. It has fixtures based on the observed formats.

Steam and steamwebhelper are AArch64 with `$ORIGIN` RUNPATH; their reported GLIBC
requirements reach 2.29. Webhelper additionally needs bundled CEF, SDL3 and Valve
libraries, X11 libraries, GL, GLib/GIO and libibus. Installed Debian supplies the
X11/GL/GLib candidates. The existing Steam libibus alias resolves into the
downloaded ARM64 runtime and needs the preserved native absolute path.

A bounded recursive static walk inspected 96 objects and exhausted its queue.
Every parsed DT_NEEDED name had a candidate in the installed Debian rootfs,
Steam's bundled paths, or the existing scoped native FEX `libfmt.so.12` import.
The ELF loader itself has no dependencies and was explicitly reported as an
unsupported/empty dependency object, not silently accepted as parsed evidence.
Guest libc provides version definitions through GLIBC2.41; installed FEX requires
GLIBC2.38. These facts justify trying the existing files without another download.

This candidate walk is **not** glibc search-order emulation or symbol relocation
validation. It does not establish dlopen plugins, per-symbol compatibility,
pressure-vessel behavior, driver/provider correctness, controller support or
actual guest resolution. Keep Debian loader/libc and scope additional paths to
the Steam process; do not globally merge Steam runtime libraries into Desktop.

## Containment and remaining gate

The active Desktop ancestor `/sys/fs/cgroup/unified/rocknix-lxc` reports populated1.
Existing game/FEX processes and the session's Xwayland occupy different children
beneath it. This supports the full-container lease design in `EXCLUSION.md`.
The native Steam scope is absent while inactive; absence cannot substitute for
the retained-parent evidence required by `scope_state.py`.

Read-only stage 0 is partially complete. Before actual Steam writes, inventory
chosen-title saves/launch options privately, ACL/xattrs and nested symlink/mount
boundaries; then qualify disposable owner0/1000/1001/65534 directory fixtures,
runtime sandboxing, and both launch directions under a concrete native gate.
No production launcher is justified yet. The next required experimental action
is stage 1 of `VALIDATION.md`, which needs explicit device-write/launch approval.
