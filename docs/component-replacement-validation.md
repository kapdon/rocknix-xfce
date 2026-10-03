# Component replacement and desktop validation — 2026-10-03

The host reuse branch was rebased onto remote `dev`
`e7f48704262a4cf91e98a5df701a815875d3a264`, including the skip-CI changelog,
native Steam scope, controller switching, and Steam recovery changes. Remote
`dev` was checked again after device testing and had not advanced.

## Exact candidate

- Built and installed commit: `73a8ca1a33b2d57ecd735477d1b75a24d44d7e90`.
- Format-2 component manifest SHA-256:
  `0be37ce2f0f652aa843976f044b3720660c02002189711ba21efbc4832bcb5dd`.
- Device: Retroid Pocket 6 / SM8550, ROCKNIX `20260930`.
- Local `bash tests/check.sh`: passed in full after correcting the installer
  fixture to expect one complete assembly for either Install or Update.
- Clean `bash build-rootfs.sh`: reused all eleven verified components in
  0.346 seconds. This is a warm local assembly/metadata result, not a cold
  compilation benchmark. Actual component production occurred earlier in
  the same local validation sequence; rebasing added no runtime byte changes.
- The local build used audited native Trash package inputs and carries
  `local_override: true`. It is deliberately not a publishable release.
- No push, tag, publication, or GitHub build was triggered.

The later Trash device-fixture correction and this report do not change the
installed runtime. Test results refer to the exact candidate above.

## Replacement and preservation

Migrated the existing legacy export installation to a complete component
rootfs, then exercised component-to-component replacement and an interrupted
activation. The updater was killed after the rootfs switch and a host launcher
write. The normal retry recovered the transaction, assembled a fresh rootfs,
completed activation, and cleared the guard. This was a process-kill test,
not a physical power-loss test.

Full home inventories immediately before and after replacement matched:
17,642 entries, approximately 11.1 GiB. Verification included content hashes,
inodes, ownership, modes, link counts, symlink targets, timestamps and xattrs.
The home root inode stayed unchanged. A separate mixed-owner fixture verified
hardlinks, symlinks and xattrs across all replacements and was removed after
validation. An old-system sentinel disappeared with the replaced rootfs.

The exact candidate was assembled from verified local components and activated
through the updater's `--assembled` path. Normal startup used the installed
Desktop Mode Tools entry. Downloaded release installation and GitHub publication
were not exercised; installer routing and publication ordering were covered by
local fixtures. The installed receipt identifies the local candidate, without
claiming a publication date.

## Runtime regression results

| Area | Observed result |
| --- | --- |
| Unprivileged boundary | UID/GID mappings, read-only host controls and narrow provider/shared mounts passed |
| Resource limits | 4 GiB memory, zero swap, PID limits and allocation/release passed; idle container about 194 MiB |
| Package management | Authenticated disposable package upgrade and interrupted configuration recovery passed; package inventory and native account databases unchanged |
| Shared Trash | Trash/discovery/read/restore, collision refusal, private-session recovery and read-only refusal passed on every mounted approved share |
| Xwayland | Accelerated GLX with packaged Mesa 25.0.7 and native Mesa 26.2.2, renderer FD740 |
| Portal chooser | Presented and selected the requested disposable file with both graphics selections |
| Native graphics/media | All ten API, readback, presentation, Firefox and MPV phases passed with actual library-map and decoder observations |
| Media lifecycle | Iris hardware H.264 at 640x360p30 and 1920x1080p30, EOF, repeated launches, software fallback and resource cleanup passed |
| FEX/Wine | Windows OpenGL probe rendered on FD740 through guest Xwayland; its separate x86 Mesa stack reported 26.2.0 |
| Keyboard/network | Guest bridge showed/hid the keyboard; screenshot inspected; guest DNS and HTTPS passed |
| Xwayland failure | Terminating the guest bridge removed mapped processes, returned to Gaming and allowed normal Desktop restart |

The Trash test formerly required five host folders even when the runtime had
correctly bound only the three that existed. It now tests every mounted approved
share without creating host directories. File chooser test development also
required the host Wayland screenshot endpoint and normal file selection rather
than externally killing the dialog; no product workaround was needed.

## Satisfactory and controllers

Both runs requested app `526870` through the installed guest games bridge as
`rocknix`, the same dispatch used by the menu. They were scripted dispatches,
not physical touchscreen menu taps. Main menus were confirmed in fresh game
logs and inspected screenshots; both used native `steam-bigpicture.scope`.

- Keep Desktop: main menu observed in approximately 79 seconds, Desktop/Sway
  remained active. Manual Desktop/Game/Automatic controller selection passed;
  automatic switching followed focus between Thunar and the game.
- Close Desktop: main menu observed in approximately 76 seconds, Desktop/Sway
  stopped while native DRM Gamescope ran. Stopping the game restored Desktop.
- Both game processes had `DISABLE_GAMESCOPE_WSI=1`, no mapped FROG WSI layer,
  and no observed swapchain assertion during the menu checks. Steam scope and
  game lease were removed and the desktop controller profile restored.

These are launch/menu smoke tests, not gameplay FPS or long-duration stability
benchmarks. Steam overlay, physical touch/controller feel, and audible output
were not requalified in this pass. Native codec reuse remains diagnostic-only;
the successful media checks used the packaged codecs with native graphics.

RP6 was left with Desktop active, Steam stopped, test-owned preservation
fixtures removed, and the original packaged graphics selection restored.
