# Steam reuse: research checkpoint (2026-10-02)

Recorded before POC implementation. No RP6 access, device writes, Steam launch,
deployment or publication is authorized or performed by this investigation.

## Baseline and evidence

The supplied worktree was clean and detached at `39fa395`, the legacy chroot
line. Fetching `origin/dev` confirmed `c1a1aec8e89b6ddeef3c9b78e58b132be5805599`.
This same worktree now uses `codex/steam-lxc-reuse` at that LXC base. Other
worktrees, including their uncommitted work, were left alone.

Fresh upstream ROCKNIX `next` source:
`9f8c79dc12c8a49db4d90232c1b9e16b19209ea6`. Sources below are relative to
[that revision](https://github.com/ROCKNIX/distribution/tree/9f8c79dc12c8a49db4d90232c1b9e16b19209ea6).

- `projects/ROCKNIX/packages/virtual/emulators/sources/Install Steam.sh`:
  client alias `.local/share/Steam` points to `games-internal/roms/steam`;
  `.steam/steam` and `sdkarm64` are aliases; `.steam/registry.vdf` is separate.
  ARM64 client, steamrt3c, custom ARM64 Proton and Arch FEX root are installed.
  libibus/libva links use absolute paths into the installed Steam runtime.
  Re-running this installer removes/replaces existing runtime data: it is not
  a safe discovery or Desktop integration operation.
- `projects/ROCKNIX/packages/emulators/standalone/steam/scripts/start_steam*.sh`:
  native ARM64 is default, x86 is optional; the common launcher inserts
  `/storage/roms/steam` into libraryfolders.vdf, uses `steam-bigpicture.scope`,
  changes binfmt, stops Sway and runs DRM gamescope. ARM64 uses
  `STEAM_COMPAT_GRAPHICS_PROVIDER` pointing into ArchLinux and restarts on 42.
  Do not source or run these scripts inside Desktop.
- `projects/ROCKNIX/packages/compat/fex-emu/package.mk`: FEX upstream commit
  `e869aa644a16e4332cdc15c1ea0b4d13d482385d`, thunks enabled, multiple native
  dependencies. Config defaults disable named thunks and contain absolute
  HostThunks/GuestThunks paths. This is not the installed RP6 binary inventory.
- Steam package version `1.0.0.85`; downloaded client/runtime versions float.
  Package version cannot identify the user's installed client or Proton.

A preliminary local distribution checkout at `d051823252f182deec126c14c95eef0970307ff9`
had materially older launch logic (optional gamescope, different binfmt and
Proton setup). It is superseded for current-source conclusions by the fresh
revision above; neither revision identifies the device firmware.

Current Desktop source: `payload/bin/rocknix-lxc{,-desktop}`, `docs/{architecture,
fex,storage}.md`, `rootfs-overlay/usr/local/bin/rocknix-fex`. Guest UID1000 maps
to host201000; guest root maps to host200000. Shared storage uses temporary
`X-mount.idmap=b:0:201000:1` binds. `/storage/Steam` is already shared **only if
it is a real root-owned directory**; the code rejects a symlink here. No broad
host home mount. ArchLinux/FEX/FEXServer/libfmt are read-only optional imports.
No X11 server/socket or DISPLAY is provisioned by this base. Private Pulse,
Wayland, render node, network and host InputPlumber desktop controls exist;
raw input, DRM primary and native administrative buses remain unavailable.

Separate local branch `codex/host-library-reuse` at `222bbb4` contains native
provider work and guest Xwayland (`85e28c8` plus fixes). It is not this base;
its worktree has ongoing documentation changes. Read as a dependency candidate,
not merged or counted as current Desktop behavior.

## Decision before coding

Conditional feasibility: share the existing client/library trees at their
native absolute paths, plus narrow aliases and selected Steam-only home state.
Prefer native ARM64 client first; FEX is needed for x86 software, not the ARM64
client itself. There is no evidence yet for functioning Steam in this LXC.

Implement offline discovery/path-planning and cooperating-launch exclusion
POCs with disposable data. Do not ship a launcher or add production mounts:
installed ABI/runtime/provider contents, X11 and controller delivery, nested
pressure-vessel behavior and bidirectional native-launch interception are not
qualified. A path or account-state file supplied by Steam is data, never host
mount authority. No blanket ownership changes and no remapping guest root to
host root. Preserve settings and prefixes; test upgrades against rollback copies.
