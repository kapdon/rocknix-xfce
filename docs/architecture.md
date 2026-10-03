# Desktop Mode architecture

Desktop Mode uses an unprivileged LXC system container.

ROCKNIX supplies Sway, InputPlumber, audio, networking and device drivers.
Desktop Mode runs Wayland and X11 applications in a Debian 13 ARM64 filesystem.
A privileged host supervisor prepares access and launches LXC using independent,
host-owned tools. Debian systemd runs as container root mapped to host UID200000;
applications and keyboard run as guest UID/GID1000 (host201000). The guest user
has authenticated container-only sudo. No-new-privileges is not imposed on the
entire session, because that would prevent sudo; browser renderers apply their
own restrictions. It is not a virtual machine or a
per-application sandbox: desktop applications share home, display, audio and
network access. Firefox's own child-process sandboxes remain enabled.

## Session lifecycle

The Tools launcher starts the installed Desktop service. Preflight verifies the
SM8550 platform/model consent, fixed endpoints, output configuration, runtime
and host tools. Only RP6 has been tested. The session records workspace,
keyboard and input state, pauses EmulationStation and keeps the host Sway alive.
Private mounts expose persistent home, selected shared storage and the limited
device/service interfaces described below.

The session starts Waybar and applications on `98:Desktop`, applies temporary
window/input rules and owns a private wvkbd process inside the Debian runtime.
A guest-owned Xwayland Satellite bridge provides `DISPLAY=:0` for legacy X11
applications, including translated Wine. It presents ordinary windows through
the existing Wayland connection; the host X11 socket is not imported. Xwayland
uses a container-local Unix socket with TCP disabled. The session waits for an
X11 query to succeed before starting applications and ends Desktop if its
bridge exits. Display-metrics refreshes leave the bridge and applications alive.
The host keyboard binary and persistent Sway configuration are not replaced.
Exit Desktop confirms before exiting; cleanup restores the previous host
keyboard/input state and EmulationStation.

The supervisor journals temporary display/decoder ACLs before granting access.
Normal cleanup restores them; the service's post-stop cleanup also recovers
orphaned setup state after a killed supervisor. Panel or keyboard failure ends
Desktop so the native Gaming environment can recover. Real compositor-loss
recovery depends on ROCKNIX's Sway service restart policy and is slower than a
panel-only failure. Recovery after arbitrary power loss is not guaranteed.

## Access boundary

- Persistent writable Debian root and home, private user/PID/IPC/mount/UTS/network
  namespaces, and temporary runtime directories. Host launchers, loaders,
  configuration and administrative helpers stay outside the guest-writable tree.
- Wayland socket, fixed SM8550 DRM render node and identified Iris decoder. No raw
  input devices, DRM primary node or root Sway IPC socket in the app runtime.
- A private Pulse socket served by a trusted, non-root audio bridge and private
  userspace networking. The native Pulse socket, administrative buses and Sway
  IPC are not exposed to Debian.
- Fixed-command controls for window switching, layout, keyboard and network
  settings. The desktop cannot submit arbitrary host commands through them.
- Network editing uses a separate non-root editor and D-Bus proxy allowing
  NetworkManager access, not the broad host system bus. Its helper uses the host's
  existing nobody UID; that shared identity is a documented limitation.
- Shared data uses temporary idmapped mounts: desktop host UID201000 writes map to
  host root ownership without recursively changing shared files. Host-executed
  `/storage/scripts` is not mounted: host maintenance scripts are not a Desktop
  dependency. Host-root SSH access is unchanged.

Native Steam is an explicit exception to the guest isolation boundary. Following
ROCKNIX's appliance model, Steam and its native launch chain run as host root in
`steam-bigpicture.scope`. Shared game storage includes Steam client/runtime/game
files that Desktop can edit; those files may later execute as host root. This is
an accepted compatibility tradeoff, not a security boundary against untrusted
Desktop applications. The games bridge validates requests but does not make
shared executable content trustworthy.
See the [native Steam decision](native-steam.md) for source evidence, scope
ownership and the deferred privilege-separation direction.

The packaged GLib/GVfs Trash handling accounts for separate home/shared bind
mounts. See the [package policy](../build-support/trash/README.md).

## Runtime and presentation

- Waybar: app launcher, context-dependent window switcher, settings,
  keyboard toggle, battery, clock and return action.
- Fuzzel: favorites-first launcher with ordinary multiword search.
- wvkbd: privately built Simple typing plus one four-row symbols page, styled
  with the same Art Book-inspired palette and Roboto as the desktop.
- Sway: tabbed apps, adaptive floating utilities and Firefox Picture-in-Picture.
- GTK and Waybar: project-provided theme; applications retain native behavior.

Output-aware sizing does not establish support for untested devices.
See [keyboard build details](../build-support/wvkbd/README.md) and
[desktop controls and window behavior](desktop-guide.md).

## Graphics and media

Mesa Freedreno/Turnip provide native Wayland OpenGL/Vulkan. MPV prefers Qualcomm
Iris H.264 decoding. Its [codec library](../build-support/mpv-ffmpeg/README.md)
preserves Debian's standard codec configuration and resets the hardware decoder
when seeking. Iris source-change notifications resume decoding after their final
capture buffer; empty notifications are recycled. Initial H.264 capture waits
for Iris to parse the stream header before allocating its buffers. Other FFmpeg
libraries remain package-managed.

Firefox uses a separate minimal pinned FFmpeg build and a profile selecting
the H.264 path. Its wrapper selects libraries only for Firefox and its children;
it does not change the host or the session's global loader environment.
Capability flags alone do not prove acceleration or reliable playback. See
[Firefox configuration and limitations](../build-support/ffmpeg/README.md).

## Installation boundaries

The installer modifies only project-owned files on writable storage. Personal
home remains separate from the persistent Debian rootfs. Shared ROM/game directories
are real host storage, not disposable copies. Debian package versions depend on
repository state at build time; image/source pins and build metadata record
provenance. The bundled keyboard source and customizations ship with the runtime.

Debian package maintenance uses normal sudo/APT from Desktop as `rocknix`.
The default password is `rocknix`; `passwd` changes it until the next system
replacement update. Root login stays locked. Container-root code executes
only through mapped LXC, never through a guest-controlled host-root loader.
The LXC updater assembles a fresh component rootfs, checks it in mapped LXC,
and replaces rootfs and host integration with rollback until activation succeeds.
Home and shared storage remain in place; system packages and edits are replaced.
No native account, keyboard binary or ROCKNIX package is replaced.

See [Install, Update and Uninstall](upgrades.md) before replacing an installation.

## Required dependencies

Native ROCKNIX supplies the kernel/device drivers, Sway/IPC, InputPlumber,
Pulse-compatible audio, NetworkManager, systemd and namespace/mount facilities. Install
checks root, aarch64/SM8550 identity, writable storage, space and host commands.
Eligible non-RP6 models require an automatic untested-device confirmation
before download or installation changes, even with `--yes`.
Preflight checks the active landscape output, compositor/frontend, native
keyboard restoration and trusted runtime files. Inspect
[installer checks](../install.sh) and [preflight](../payload/bin/preflight)
for exact gates; Debian APT is inside the container, not native ROCKNIX.

The separately bundled [host tools](../build-support/lxc/Dockerfile.host-tools)
include LXC, uidmap, ACL/mount utilities, slirp4netns, PulseAudio, bubblewrap,
D-Bus proxy and the network editor. Bubblewrap isolates the trusted non-root
audio/network helpers through `rocknix-helper-sandbox`; LXC owns the desktop
application session. Trusted helper loaders/libraries come
from host-owned tools, never writable guest Debian.

The [guest image](../Dockerfile.rootfs) provides systemd, sudo/APT, apps,
Waybar, GTK/Qt Wayland libraries, Mesa, patched GLib/GVfs, private Fuzzel,
wvkbd and Firefox FFmpeg. Optional native FEX is described separately in
[FEX reuse](fex.md); its absence does not prevent ordinary Desktop startup.

See [building](build.md) for build-host dependencies and
[storage](storage.md) for backup boundaries.

The [device guide](devices.md) specifies the fixed
SM8550 endpoint checks and device confirmation rules for versioned and
development builds. Host-owned
`managed/host/state/device.json` allows installed session/maintenance use on
the same model; it grants no guest control over devices, paths or profiles.
Only RP6 has been tested.
