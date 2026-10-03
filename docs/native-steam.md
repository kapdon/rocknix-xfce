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
  silent alternate launcher.
- `rocknix-desktop-games.service` supervises Desktop transitions, the available
  memory guard and controller focus. Steam and its children live in the native
  scope, not the supervisor service. Focus detection follows scope membership.
- Stop/failure recovery stops the native scope before restoring binfmt,
  controller profiles and Desktop. Failed cleanup retains the journal. The
  native scope receives the session task limit after it appears.
- Maintenance checks refuse a live Steam scope, an active/transitional supervisor
  or an unfinished session journal. This covers the interval after the
  supervisor releases its lock and before recovery completes.

Both modes retain the previously validated common SDR policy that disables the
optional Gamescope WSI bypass. This is a Desktop launch policy, not a firmware
modification. Scope reuse does not imply that Keep mode inherits every native
game setting or Steam-update restart behavior.

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
WSI policy, controller scope membership, cleanup ordering, failed cleanup journal
retention, idempotent stop and maintenance exclusion. Device results are recorded
in [the Steam experiment log](../experiments/steam-lxc/NATIVE-FPS.md).

An early native-scope attempt hit a full `/dev/shm` and Steam's SIGBUS. Inspection
found 1,012 unreferenced root Steam `u0-Shm_*` files occupying 6,005,923,840 bytes.
They were removed with Steam stopped after checking open descriptors and memory
maps. This was dev-device cleanup, not an automatic deletion policy in the product.
