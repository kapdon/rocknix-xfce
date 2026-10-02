# Native Steam beside the LXC desktop — RP6 investigation

## Conclusion

**Feasible and demonstrated for Steam's desktop UI.** The LXC desktop can stay
running while host-native gamescope presents host-native Steam as another window.
Steam loaded the existing account/library, including installed Satisfactory, and
accepted pointer input to open Add a Game → Add a Non-Steam Game. Steam remained
outside LXC; Thunar and the desktop panel remained inside. No remote streaming or
copy of the Steam installation is involved.

**Not yet a complete management workflow:** Browse in the non-Steam dialog failed
to open a file chooser. Steam logged `failed to retrieve file open dialog results`.
No file-chooser portal was installed on the host or in the guest, no portal owned
the host session bus, and the tested Steam environment had no explicit session-bus
address. Portal/session integration is the next concrete requirement. Adding a
shortcut, installing Windows dependencies, controller gameplay, audio, and running
Satisfactory under nested gamescope were not qualified in this investigation.

## Evidence and environment

RP6 firmware `9fd38fa`, installed Desktop `222bbb4`, gamescope `fa0b4d3+`, Steam
client 1790377368. These are installed-device results, not a build of this branch.
The existing verified Steam backup remains at
`/storage/steam-lxc-backup-20261002/native-steam.tar`.

The first native UI test showed:

- Host Steam: PID namespace `4026531836`, mount namespace `4026531832`, cgroup
  `/system.slice/native-steam-poc.service`.
- Guest Thunar: PID namespace `4026533395`, mount namespace `4026533392`, cgroup
  beneath `/rocknix-lxc/lxc.payload.rocknix-lxc-1`.
- Host Sway saw a normal `app_id=gamescope` surface beside `app_id=thunar` in
  workspace `98:Desktop`. The existing panel counted both windows.
- gamescope connected to host `wayland-1`; Steam received gamescope's private
  Xwayland `DISPLAY=:1` and no WAYLAND_DISPLAY. It did not bypass gamescope.
- Existing library/account state loaded. No container GTK packages, runtime idmaps,
  writable runtime-lock overlay, or imported guest Vulkan provider were required
  for this native Steam process. Earlier guest test residue still exists but is
  outside its namespaces and is not evidence of a dependency.

Screenshots and raw logs are private local artifacts rather than committed account
information. A screenshot of the non-Steam dialog has no account/wallet header.

## Display architecture

The current desktop is not a nested guest compositor. LXC apps connect through
an existing restricted Wayland bridge to **host Sway**. Therefore the proposed
arrangement is:

```text
Host Sway / physical display
├── LXC desktop apps: Waybar, Thunar, keyboard, browser
└── Host gamescope (Wayland backend)
    └── Host Steam desktop UI + its native Proton/game children
```

A game may use Steam's own pressure-vessel namespaces, just as in native ROCKNIX;
that does not make it an LXC game. Graphics/CPU translation stay in the native
runtime. The LXC filesystem and user mappings need not service Steam updates.

The native ROCKNIX launcher cannot be called unchanged: it stops Sway and starts
DRM gamescope, disrupting Desktop. A separate entrypoint must preserve host Sway,
use a nested backend and keep native preparation/cleanup correctly scoped.
[Gamescope upstream](https://github.com/ValveSoftware/gamescope#readme) documents
both nested desktop operation and standalone DRM operation.

## Physically tested launch configuration

[native-gamescope/session.sh](native-gamescope/session.sh) records the final tested
launch body, with added explicit dev-device guards. It uses native HOME=/storage,
the existing ARM64 Steam libraries and FEX graphics-provider JSON, and:

```text
gamescope --backend wayland -W 1280 -H 720 -w 1280 -h 720 -r 60
  --xwayland-count 2 --force-windows-fullscreen --
  steamrtarm64/steam -deckard -steamos3 -nobigpicture -noshaders
  -silent steam://open/games
```

Run only in a supervised transient host unit with KillMode=control-group,
TimeoutStopSec=15, TasksMax=1000 and RuntimeMaxSec=300; launch the independent
[native-gamescope/watch.py](native-gamescope/watch.py) first. The watchdog stops
that exact unit at five minutes or below 1.5 GiB MemAvailable. The saved script
requires `--run-on-rp6-dev`. It is a reproduction artifact, not a production gate
or installer, and must not race any other Steam launch.

The session temporarily disables x86/box32/box64 binfmt handlers as the installed
ARM64 native launcher does, and restores their captured states on exit. A hard
kill can skip shell cleanup, so the supervisor must eventually own durable recovery
for these global settings. This test explicitly checked restoration of all three.
Unlike the original native launcher, the POC did not remove compatibilitytool.vdf.

Test variants:

- Wayland with gamescope `-e`: native Steam rendered the initial offers dialog.
- Wayland without `-e`, with `-silent steam://open/games`: desktop library and
  non-Steam dialog worked. Offers were suppressed.
- SDL-on-Wayland with one Xwayland: processes started, but no surface appeared in
  the observation window. Both backend and count changed; cause is unresolved.
- Wayland with two Xwaylands and force-windows-fullscreen: usable full-size
  non-Steam dialog. Synthetic Sway IPC clicks were inconsistent; temporary uinput
  mouse events with normal kernel timestamps operated the menus reliably. The
  temporary input device was destroyed after each interaction. This is not a
  physical touchscreen/controller acceptance test. The earlier apparent pointer
  bug cannot confidently be attributed solely to gamescope's coordinate mapping.

## Missing file chooser and dependency workflow

The host has GTK2/GTK3 libraries, but no xdg-desktop-portal frontend/GTK backend at
standard paths or activation service. The guest lacks them too. The downloaded
ARM64 client runtime includes zenity, but zenity is not itself a portal provider.
The bounded runtime scan found portal checkers, not a portal frontend/backend.

The [FileChooser API](https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.FileChooser.html)
returns a request handle and then a response containing selected file URIs.
A direct Steam report records this exact Add Game request in
[Valve's issue tracker](https://github.com/ValveSoftware/steam-for-linux/issues/11831).
Missing portal support is an observed integration gap and the leading explanation
for our failure; it has not yet been fixed and retested.

Two implementation candidates require a focused POC:

1. Package a matching host-native portal frontend/backend and launch it on the
   same dedicated session bus as native Steam. Reuse host GTK where compatible.
   This avoids crossing user/mount namespaces for returned paths.
2. Provide a narrowly scoped FileChooser bridge to a guest dialog. Return only
   native-resolvable shared-storage paths, preserving URI encoding, cancellation,
   filters, and request ownership. A raw connection to the guest bus is not enough:
   UID mapping/authentication and filesystem paths differ. Do not expose the host
   system bus or add arbitrary host-command execution to LXC.

For Windows dependencies, the installer must run with the title's **native Proton
version and prefix**. A desktop file manager can download/extract installers into
shared storage, but guest apt packages do not install dependencies for native games.
A future title-specific host helper should take structured title/installer choices
and reject unmapped paths; no dependency installer was run in this investigation.

## Proposed integration and remaining acceptance

Reuse the existing bounded host-control FIFO pattern for a fixed `steam` action.
A guest desktop shortcut requests launch/focus; the host validates Desktop state,
takes the common Steam lease, starts one fixed native service, and publishes state.
Do not pass a guest-supplied shell command to root. Native Gaming Mode must use the
same lease **before** its existing preparation code. Client singleton behavior
alone is not launch-race protection.

Bind the native session lifecycle to Desktop: request graceful Steam shutdown on
Exit Desktop, bound the wait, then remove all owned children and restore global
state before resuming Gaming Mode. Window switching can use existing Sway window
policy; its surface is already counted. Test close/reopen, keyboard, focus, controller
routing and clipboard explicitly. Desktop InputPlumber mappings may need a distinct
game-focus policy so game controls do not also trigger desktop shortcuts.

Next tests: working Browse/select/cancel with native paths; a disposable non-Steam
shortcut and Windows installer; nested game launch with audio/input/save/load;
return to ordinary native Gaming Mode; launch-race and crash cleanup tests. Start
with a bounded lighter workload before retrying Satisfactory with LXC open.

## Resource observations and cleanup

Before this investigation, host Sway retained ~3.65 GB RSS+swap after the previous
failed LXC game experiment. Restarting Sway while Desktop was stopped released
some pressure. This suggests compositor allocations outside the LXC cgroup helped
make the earlier memory limit ineffective; it is not a proven leak diagnosis.

After Desktop startup, MemAvailable was ~7,057 MiB. Native Steam UI observations
were ~4,917–5,480 MiB available. These are point samples, not a precise incremental
memory benchmark or gameplay budget. The UI tests did not freeze SSH. Swap already
contained ~3.15 GiB from earlier activity and remained occupied.

Cleanup verified: no processes remained in the experimental native Steam cgroup;
x86, box32 and box64 handlers were enabled again; ordinary Desktop stayed active.
Final observed MemAvailable was 6,432 MiB. No new package, production launcher,
container mount, bus bridge or permanent service was deployed for this experiment.
Steam's ordinary shared-state/log writes remain; the backup is retained. Prior LXC
test residue and the unverified native game round trip remain recorded separately
in [GAME-TEST.md](GAME-TEST.md).
