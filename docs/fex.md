# Optional native FEX reuse

Desktop remains a Debian ARM64 container. On the RP6, optional x86 translation
reuses ROCKNIX's existing Arch x86 filesystem and native FEX implementation.
No separate Ubuntu translation filesystem is provisioned by Desktop.

The host-defined mounts expose only:

| Host source | Container destination |
| --- | --- |
| `/storage/.local/share/fex-emu/RootFS/ArchLinux` | `/run/rocknix-fex/ArchLinux` |
| `/usr/bin/FEX` | `/run/rocknix-fex/bin/FEX` |
| `/usr/bin/FEXServer` | `/run/rocknix-fex/bin/FEXServer` |
| Resolved `/usr/lib/libfmt.so.12` | `/run/rocknix-fex/lib/libfmt.so.12` |

All four mounts are read-only, nosuid and nodev. Native binaries and their
ancestors must be root-owned and not group/other-writable. The Arch root may
also belong to native UID1000, as in ROCKNIX's unpacked image; ancestors must
remain native-root-controlled. Container identities map to different host IDs.
No broad host library directory, host loader, host libc or administrative
socket is exposed. Translation executes inside the container as its caller,
never as native host root.

`/usr/local/bin/FEX` delegates to `rocknix-fex`, which selects the mounted Arch
root and scopes the native library search directory to the translator process
and children. It does not edit host or user FEX configuration. Container-admin
changes to this wrapper do not become host-executed code.

Missing Arch data or native runtime files disable this optional capability;
ordinary Desktop startup remains available. Unsafe sources still fail closed.
The wrapper reports unavailable translation with exit 126. The dependency set
is RP6-specific, not a claim that arbitrary ROCKNIX FEX releases are compatible.
After a host update, a new Desktop session picks up the host files; dependency
and ABI compatibility must still be checked. Do not update host runtime files
during an active translated application session.

## X11 applications

The Desktop session supplies a guest-owned Xwayland server through Xwayland
Satellite and exports `DISPLAY=:0`. FEX/Wine applications launched from Desktop
inherit that display. The server uses the existing Wayland bridge to present
windows on native Sway; no native X11 socket is shared. Session shutdown also
terminates translated applications and their detached Wine services.

When reusing a PD2 Launcher download cache across devices, let the Launcher
reverify payloads in a fresh home. Its retained transaction journals and download
receipts contain filesystem/inode identities and cannot be copied as valid
state. Preserve the original home; import cached installer/client payloads
without its `.pd2launcher-retained` directories or old `downloads.json` receipt.

## X11 work area

The session publishes Sway's usable Desktop workspace to X11 as `_NET_WORKAREA`
and `_GTK_WORKAREAS_D0`. Panel and on-screen keyboard reservations update these
bounds; window decorations and individual tiled allocations are separate. The
bridge matches the output to its RandR monitor and translates logical bounds
into X11 pixels. It does not expose the host Sway control socket to the guest.

Wine runners can override that information. In particular, the tested Wine-GE
8-26 fullscreen-hack handler replaces the work rectangle with the full monitor.
See the [windowed-mode investigation](PD2_WINDOWED_SIZE_HANDOFF.md) for the
verified API behavior and launcher-owned follow-up; Desktop does not globally
change Wine fullscreen policy.

## Compatibility limits

FEX availability does not guarantee that an x86 application will work. Graphical
applications and controller support depend on the application and translator.
Ordinary Desktop remains ARM64; native ROCKNIX FEX packages are outside Desktop
update and uninstall.
