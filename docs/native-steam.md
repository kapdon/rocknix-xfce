# Native Steam integration decision

Decision recorded 2026-10-03: prioritize compatibility with the installed ROCKNIX
Steam launcher and reuse its native scope. Accept ROCKNIX's host-root execution
model for this version. Privilege separation is future research, not a release
requirement for this integration.

## Source and runtime evidence

The reference checkout is `/home/nexus/code/rocknix-distribution`, updated to
ROCKNIX `upstream/next` commit
[`4a92dd9202eec29514705d84a68f0a7f602adfac`](https://github.com/ROCKNIX/distribution/tree/4a92dd9202eec29514705d84a68f0a7f602adfac).
Its original `next` tracking branch followed the older fork `origin/next`;
updating that fork alone did not update it to current ROCKNIX.

- `projects/ROCKNIX/packages/ui/emulationstation/system.d/essway.service` sets
  `HOME=/storage` and does not select `User=`. It is a root system service.
- ROCKNIX packages systemd 255.8. That version sets `USER=root` for a system
  service without an explicit user; the profile also sets `HOME=/storage`.
- `steam_scope_reexec_if_needed` in `start_steam.sh` invokes
  `systemd-run --scope --slice=system.slice --unit=steam-bigpicture --collect`.
  It forwards `_STEAM_SCOPE`, `HOME`, `USER` and `TZ` as environment variables.
  `-E USER=...` does not change process credentials.
- `start_steam_arm64.sh` prepares native state and invokes that helper before
  launching Gamescope and Steam. There is no privilege drop in this script chain.
- The `USER` fallback in FEX's `package.mk` belongs to its build, not Steam's
  runtime user selection.

The installed RP6 scope helper matched the updated reference function byte for
byte (SHA-256
`6d0f546ecbd29fbcba69935e0a3984268b5a359abe80422297846f01afa74093`).
A native launch using EmulationStation's captured environment, without Desktop's
Steam wrapper, observed EmulationStation, Gamescope, Steam and wineserver with
real/effective UID 0 in the host user namespace. That particular run encountered
Proton/Wine startup errors before the Satisfactory executable was captured; it
does not establish credentials for every possible game/runtime descendant.
Subsequent Desktop integration tests captured Satisfactory itself with host UID 0
inside the native scope in both launch modes; see the validation log below.

## Current design

One shared Steam installation and game library remain editable from Desktop.
No recursive ownership changes, second Steam installation, separate Proton
library or changes to the installed ROCKNIX scripts are required.

- **Close Desktop:** resolve the native `.desktop` shortcut and invoke installed
  `runemu.sh`. Allow ROCKNIX to create `steam-bigpicture.scope` normally, choose
  DRM presentation and apply native game settings.
- **Keep Desktop:** source the installed Steam scope helper and let it re-execute
  our nested-session entry point in the same native scope. The full native
  launcher currently selects DRM and stops Sway, so the nested Gamescope command
  remains Desktop-specific. A missing helper fails explicitly; there is no
  silent alternate launcher. Keep mode captures Steam's own exit status and
  restarts the nested session on its update/restart code 42 within the same scope.
  Normal exits, compositor failures without a client restart request, and stop
  signals end the session.
- `rocknix-desktop-games.service` supervises Desktop transitions, the available
  memory guard. Steam and its children live in the native scope, not the
  supervisor service. Desktop owns the always-available one-tap controller
  override. Until tapped, automatic focus detection recognizes the native Steam
  scope and Gamescope Wayland clients in the mapped LXC. After a tap, the choice
  stays manual for the rest of that Desktop session.
- Stop/failure recovery stops the native scope before restoring binfmt,
  Desktop when it was closed. Manual controller selection in a retained Desktop
  survives game exit. Failed cleanup retains the journal. The
  native scope receives the session task limit after it appears.
- Maintenance checks refuse a live Steam scope, an active/transitional supervisor
  or an unfinished session journal. This covers the interval after the
  supervisor releases its lock and before recovery completes. The standalone
  installer checks before and after acquiring its lock, before downloading;
  copied updaters resolve this guard from their trusted helper directory.

Both modes retain the previously validated common SDR policy that disables the
optional Gamescope WSI bypass. This is a Desktop launch policy, not a firmware
modification. Scope reuse does not imply that Keep mode inherits every native
game setting.

## Nested virtual display sizing

**Settings → Gamescope settings → Virtual display · fit desktop** controls the
initial resolution for nested launches. It defaults to On, including when
upgrading older settings. On uses the current tiled client content
size published by the host Sway policy, excluding its decorations. If there are
no tiled clients, it uses the usable workspace bounds. Output scale converts
logical Sway dimensions to display pixels. Missing, invalid or stale geometry
fails the launch instead of silently substituting a guessed resolution.

For example, a current 1920×953 client gives Gamescope `-w 1920 -h 953` and
`-W 1920 -H 953`. This is a launch-time snapshot: opening a new tab, splitting a
workspace, showing the keyboard or moving the window can change the actual
allocation afterwards. Gamescope scales the complete internal display into its
outer window; the game resolution stays fixed until the next launch. This
avoids requiring legacy games to resize their rendering buffers. Aspect-ratio
differences can produce letterboxing. The game must still support the selected
resolution and its own fullscreen behavior inside that display.

The setting applies to Steam **Keep Desktop** launches. **Close Desktop** still
uses ROCKNIX's unchanged native DRM launch path. Gamescope always provides an
isolated display; Off uses the monitor's full resolution, without subtracting
panels or tabs. It does not revert to a fixed 720p resolution.
Changing either setting preserves the other and affects only future launches.

**Apps → Launch with Gamescope → choose an app** uses the same installed
`.desktop` catalog as normal Apps. The Gamescope entry is kept first when Apps
opens with an empty search; typing still filters normally. Other app usage
counts are preserved. The Gamescope picker has its own usage ordering.
Both this entry and Steam games use the installed Adwaita `input-gaming` icon.

Close existing instances before using this path: an application may otherwise
forward the request to its existing process outside Gamescope. This option is
for X11/Wine applications; Wayland-only applications should use normal Apps.
Steam games and shortcuts that already start Gamescope should also use normal
Apps. Launch failures show a menu and write
`~/.local/state/rocknix-desktop/gamescope-app.log` (or `$XDG_STATE_HOME`).
The original desktop entries and Wine/game settings are not rewritten.

LXC programs can also use the same policy from a terminal:

```sh
rocknix-gamescope -- wine /path/to/game.exe
rocknix-gamescope -- rocknix-fex /path/to/wine /path/to/game.exe
rocknix-gamescope --virtual-display off -- /path/to/game
```

Commands and arguments are passed directly, without shell evaluation. This
launcher targets X11/Wine games, uses the guest SDL/Wayland backend, and retains
the shared WSI-disable baseline. Its children select X11 so they cannot bypass
the virtual display by connecting to the outer Wayland compositor. Direct calls
to the upstream `gamescope` binary and applications with their own compositor launch logic
are not intercepted. The guest base includes Debian's Gamescope backport; no
host library tree or additional DRM primary device is exposed for it.

The host and guest packages contain the same sizing helper from one canonical
source. Source regressions cover toggle persistence, legacy settings, content
bounds, scale, stale/invalid geometry, argument preservation, native DRM routing
and Steam restart behavior. The display policy was installed on RP6 at `fd0c7c2`: X11 probe checks covered
fit/native dimensions and keyboard resizing, and the user confirmed PD2
fullscreen works through a Gamescope-wrapped launcher. This does not qualify
all games, physical input or frame times. The later generic Apps picker was applied as a live UI preview without restarting
LXC. RP6 checks verified its pinned entry and icons, real Fuzzel selection into
Gamescope, quoted arguments and working directory, and normal launches remaining
on the outer display. Fullscreen game acceptance remains the user's PD2 test.
Debian Gamescope was observed aborting during teardown after a clean probe exit;
the app prefix records the child's exit status so that teardown does not falsely
report a failed application launch. The compositor teardown issue itself is not
fixed by this change.

## Accepted trust tradeoff

Installing games, editing prefixes, adding mods and managing non-Steam games
need access to their files, not inherently host-root privileges. Desktop's
idmapped shared mounts provide that access without changing stored ownership.

However, shared executable content can subsequently be loaded by host-root
Steam, Proton or Gamescope. The fixed-command request bridge is not a security
boundary against software that can modify that content. This is an explicit
compatibility choice matching ROCKNIX's appliance model. A small root helper
that merely validates an app ID and launches root Steam would retain this risk.

Native Gaming Mode does not participate in Desktop's advisory launch lock.
Already-running native Steam is rejected, but an external simultaneous native
launch/replacement of the single scope is not qualified. The scope helper is an
installed script function rather than a documented stable API; firmware changes
still require integration validation.

## Deferred privilege-separation direction

The preferred research direction is a small privileged session manager for
display handoff, device access, system settings and recovery, with Steam, Proton,
FEX and games executing under an unprivileged identity. Reuse the existing files
through scoped access/mappings rather than copying libraries or changing their
ownership. Qualify nested graphics first, then direct DRM, controllers, audio,
client/game updates, non-Steam games and recovery.

ROCKNIX currently combines privileged preparation and execution. A maintainable
solution would introduce an explicit upstream launch boundary; merely adding
`User=` to the existing launcher would break privileged operations. Root processes
must also avoid loading libraries/plugins from the writable Steam tree before
that boundary.

Protecting only Desktop-origin launches would leave native Gaming Mode's root
execution of the same writable files unchanged. Full isolation needs both launch
paths to adopt the boundary, or separate/protected executable storage. Keeping
unmodified root launching, arbitrary writable shared executables and strong
guest-to-host isolation simultaneously is not a supported security claim.

## Validation boundaries

Source tests cover native-helper routing, inherited identity variables, shared
WSI policy, manual controller selection, cleanup ordering, failed cleanup journal
retention, idempotent stop, Steam restart/stop behavior and maintenance exclusion
through recovery and copied updater entry points. The restart and maintenance
regressions use local fixtures; no new device qualification is claimed. Device
results are recorded in [the Steam experiment log](../experiments/steam-lxc/NATIVE-FPS.md).

An early native-scope attempt hit a full `/dev/shm` and Steam's SIGBUS. Inspection
found 1,012 unreferenced root Steam `u0-Shm_*` files occupying 6,005,923,840 bytes.
They were removed with Steam stopped after checking open descriptors and memory
maps. This was dev-device cleanup, not an automatic deletion policy in the product.
