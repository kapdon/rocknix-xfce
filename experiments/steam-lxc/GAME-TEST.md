# Satisfactory on RP6 LXC — 2026-10-02

## Result

**Partial startup, not a gameplay pass.** Satisfactory (Steam app 526870, installed
build 24656030) rendered its loading screen inside the unprivileged Desktop LXC.
Its log reported `Game Engine Initialized` and `GDynamicRHIName Qualcomm Vulkan`.
No main menu, playable scene, audio, controller, save/load, or native round trip
was verified. The device subsequently exhausted available RAM and swap and became
unresponsive to SSH. SSH later recovered; see the recovery follow-up below.

This uses firmware `9fd38fa` and installed Desktop `222bbb4`, with a temporary
adapter; it does not validate this branch's production payload. The user reports
that this installed title already works in native ROCKNIX.

## Protecting shared state

With Desktop/native Steam stopped, created a GNU tar archive with numeric owners,
ACLs and xattrs of both Steam libraries and `/storage/.steam` at
`/storage/steam-lxc-backup-20261002/native-steam.tar` (~44 GB). A full `tar --compare`
returned 0 with zero differences before execution. Native rsync could not provide
ACL/xattr preservation, so its unsuccessful invocation was not used as a backup.
The archive and original installed supervisor remain on RP6. Private account
state and raw client logs are not committed.

## Experiment changes

- Existing root-owner idmapped library mounts provided the shared client, games,
  Proton, prefixes and saves. Added `/storage/.steam` under that same mapping.
- Overlaid the ARM64 client runtime read-only using native UID65534→guest1000;
  overlaid its real `.ref` writable with the same mapping, explicitly approved.
- Synthetic guest `/storage` aliases resolve the original Steam/library/FEX paths.
  Added guest `/usr/bin/FEX` alias to the installed wrapper and a guest-only FEX
  config pointing to `/run/rocknix-fex/ArchLinux`.
- Installed Debian `libgtk2.0-0t64` and `libgtk2.0-common` (2.24.33-7). Steam's
  dlmopen of steamui.so otherwise failed on `libgtk-x11-2.0.so.0`.
- Enabled the installed optional native Vulkan provider. Debian Turnip 25.0.7
  failed the DXVK storageBuffer8BitAccess requirement; native Turnip 26.2.2 was
  recognized as Adreno 740. This provider imports selected matching dependencies
  and keeps the guest loader/libc.
- Steam's transient unit needed TasksMax1200 after the inherited 230 task limit
  produced fork EAGAIN. Outer container task limit remained 1536.
- Raised the live container memory cap from 4 GiB to 8 GiB after memory pressure.
  This change is transient; the ordinary supervisor defaults remain unchanged.

No host X11 socket, raw input, host system bus, native gamescope, or binfmt change
was introduced. These are supervised experiments, not production exclusion.

## Actual launch sequence

Steam reused the existing account and logged in, but remained at “Loading user
data” / WaitingForLibraryReady. `-applaunch 526870`, both alone and with native
`-deckard -steamos3 -gamepadui -noshaders`, did not create a game process. Steam's
graphics probes ran; those are not Satisfactory evidence. Probe startup modified
compatdata/0 while checking installed compatibility tools.

A separate guest UID1000 transient service invoked the existing
`SteamLinuxRuntime_4-arm64/_v2-entry-point --verb=waitforexitandrun`, followed by
`Proton 11.0 (ARM64)/proton waitforexitandrun`, the installed FactoryGameSteam.exe,
and native `-NO_EOS_OVERLAY`. It reused compatdata/526870 and set the corresponding
Steam app/library/install paths. Steam was still logged in when this direct launch
started. **This bypassed the stuck client UI; it is not a successful Steam Play
button or client-managed game launch.**

The physical DSI-1 display capture showed the Satisfactory loading screen. At
17:58:30 UTC its game log initialized Unreal Engine and identified Qualcomm Vulkan.
The last resource sample showed 11,462 MiB RAM, only 216 MiB available, all 6,143 MiB
swap consumed, and memory.events `oom_kill 1`. The counter alone does not identify
the killed process. Stopping Steam's unit and killing the disposable LXC cgroup
could not be confirmed because SSH stalled/timed out. No successful recovery or
cleanup is claimed.

## Reproduction and recovery

`game-test/` records the temporary adapter and launch commands. They require the
exact prepared guest mounts, aliases and packages above and are not an installer.
The adapter was inserted before the installed supervisor's main entrypoint;
original and patched hashes are in the backup's adapter-hashes.json. Launch scripts
require `--run-on-rp6-dev`. Do not run them on an unprepared or production device.

After RP6 responds:

1. Confirm no native Steam or game process is active. Stop Desktop and verify its
   container and experimental mount staging have been removed.
2. Recover private diagnostic logs if useful. Restore the original installed
   `host/bin/rocknix-lxc` from rocknix-lxc.original, verifying its recorded SHA256.
3. Remove `host/state/native-providers` (originally absent) if returning to baseline.
   Guest GTK packages and synthetic aliases are test residue in the disposable
   rootfs; do not remove any native Steam data when cleaning those paths.
4. Compare/restore shared state from the metadata-preserving archive while all Steam
   processes are stopped. Account/client logs, bootstrap compatdata/0, Satisfactory
   compatdata/526870 and shader state may have changed. Never recursively chown.
5. Restore ordinary Desktop or Gaming Mode and explicitly verify native launch.
   Keep the archive until preservation and recovery are established.

Further game work needs a host-memory budget that includes graphics allocations,
Steam UI and nested runtimes, bounded diagnostics and a reliable watchdog outside
LXC. The 8 GiB cgroup cap did not prevent host exhaustion in this run. Resolve the
client library-ready stall separately; do not turn the direct Proton diagnostic
into a claim of complete integration.

## Recovery follow-up

A fresh SSH check succeeded without a confirmed reboot. Memory was still severely
constrained (378 MiB available, all swap consumed). Stopped Desktop and terminated
its remaining disposable cgroup; service then reported inactive/dead, with 5,942
MiB RAM available and EmulationStation running. Swap remained largely occupied.
Restored the original installed supervisor and verified its recorded SHA256;
removed the temporary native Vulkan selection. No experimental host mounts remained.
The native Steam backup is retained. Guest test packages/aliases and shared Steam
state changes have not been rolled back; native game compatibility remains unverified.
