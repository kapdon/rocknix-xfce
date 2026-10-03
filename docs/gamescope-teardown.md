# Guest Gamescope teardown

A PD2 session left `gamescopereaper` and a detached `winedevice.exe` alive after
Gamescope exited. Wine retained the launcher/game locks and controller event
handles. The installed reaper sends TERM and waits without a bounded escalation;
a process-group-only fix cannot contain a helper that calls `setsid()`.
Upstream [3.16.22 reaper source](https://github.com/ValveSoftware/gamescope/blob/3.16.22/src/Apps/gamescopereaper.cpp)
and [issue 1482](https://github.com/ValveSoftware/gamescope/issues/1482)
match this failure pattern. The separate SDL teardown abort lacks a backtrace;
this change contains its consequences rather than claiming an upstream repair.

## Lifetime boundary

`rocknix-gamescope` now creates a unique transient **user service**. Its
supervisor watches both the primary application and compositor. Primary exit
requests compositor shutdown, with a three-second grace before KILL. Compositor
exit ends the supervisor; systemd terminates all remaining service descendants,
including detached Wine helpers, with five-second TERM-to-KILL escalation.
Cleanup is accepted only once the unit is inactive/failed with no control group.
It never uses process-name killing or prefix-wide `wineserver -k`.

The original argv, working directory and desktop environment travel in a private
0600 request file. Only systemd control commands use `/run/user/1000/bus`; the
application retains the existing Desktop D-Bus and Wayland endpoints. The guest
user manager persists while LXC is running. Container shutdown ends its services.
No host account, native Steam launcher or native Steam scope changes.

The native FEX server starts separately as `rocknix-fex-server.service`, UID1000,
with its own runtime directory. Its readiness pipe gates Desktop startup, and
wrapped launches require it to be active when the native FEX provider exists.
This prevents the first game from owning a shared server inside its cleanup
boundary. FEX still uses the existing native binaries/rootfs and user config.

Direct `gamescope` calls bypass this wrapper. Apps forwarding into an existing
instance or an external D-Bus service cannot be pulled into this launch's group;
close existing instances first. Deliberately delegated user services are also
outside the boundary. Concurrent Wine apps sharing one prefix may already share
a wineserver: this does not create independent Wine-prefix ownership.

## Verification, 2026-10-03

Base: local `dev` at `0ab1ea5`; feature branch `fix/gamescope-teardown`.
Runtime checks used a backed-up **source-file preview** on the existing RP6 LXC,
not an installation of a freshly assembled release. Existing game data, Wine
registry and runner configuration were preserved.

- Project `tests/check.sh` passed, including component assembly with the exact
  FEX service and guest linger file admitted to the managed namespace.
- Real local subprocess tests covered app success/failure, compositor abort,
  compositor ignoring TERM, argv/environment preservation and cleanup refusal.
- RP6 reaper fixtures used detached TERM-resistant children. Normal exit returned
  success after cleanup; compositor SIGABRT retained status 134. Both removed
  the detached child in roughly 5.4 seconds and preserved an unrelated process.
- Real PD2 Play reached the game menu. Game, Wine, reaper and compositor were
  confirmed inside one user service; the shared FEX server was outside it.
- WM_DELETE_WINDOW closed the game and launcher. The compositor needed the
  three-second KILL fallback; all Wine/Gamescope descendants disappeared.
  The app outcome stayed 0, with forced compositor shutdown recorded separately.
- Relaunch succeeded. Killing that compositor while the game ran removed all
  16 recorded session processes in 5.3 seconds. An independent FEX `/usr/bin/sleep`
  and the same shared FEX server remained alive.
- Desktop shutdown with a wrapped launcher active removed all 38 recorded guest
  user processes in 1.73 seconds, restored Gaming with host Sway retained, and
  restarted successfully.
- Another relaunch followed by foreground-client TERM left no session processes
  or open PD2 launcher/game lock handles. The shared FEX server survived.

Preview startup testing also caught and corrected FEX's optional `-p` argument
ordering and an unsafe shared RuntimeDirectory. The final FEX service owns
`/run/rocknix-fex-server`; it cannot remove Desktop's Wayland link when stopping.
The upstream compositor abort, long-run gameplay, physical input and final
release-bundle qualification remain separate acceptance items.

Per-launch JSON under `~/.local/state/rocknix-desktop/gamescope-sessions` records
application/compositor outcomes and confirmed cleanup. Normal picker output is
in `gamescope-app.log`. A cleanup timeout is not concealed: a successful app may
return success only after the service's empty cleanup boundary is confirmed.

Preview originals are stored in the guest's
`/var/lib/rocknix-desktop/teardown-preview-backup` with an existence/mode manifest.
Rollback requires closing Desktop apps, restoring those exact files, removing
preview-only files and disabling guest linger only if its manifest says it was
previously absent, then restarting Desktop. Do not delete the user's home or
restore unrelated Wine configuration. A clean component installation remains
the release-validation path; this backup is only for the scoped preview.
