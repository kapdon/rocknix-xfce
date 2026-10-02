# Staged RP6 validation and recovery

Stage 0 read-only inventory has partially run; see [INSTALLED.md](INSTALLED.md)
for actual evidence and remaining inspection gaps. No stages 1–4 have run.
Existing device access is available. Read-only inventory is within research scope.
Stages 1 onward change device
state or launch software and require separate explicit authorization. Keep all
collected account data private; publish only redacted findings and version IDs.

## 0. Read-only inventory before designing installable integration

Record firmware release/model, installed Desktop build-info, kernel, active
mounts and native Steam scope. Use existing SSH access, not guessed credentials.
Suggested host commands (adapt unavailable tools after `command -v` checks):

```sh
cat /etc/os-release
uname -a
tr -d '\000' </proc/device-tree/model
systemctl show steam-bigpicture.scope -p ActiveState -p SubState -p ControlGroup
cat /proc/self/mountinfo
readlink -f /storage/Steam /storage/.local/share/Steam /storage/.steam /storage/roms/steam
stat -c '%u:%g %a %F %n' /storage/Steam /storage/.local/share/Steam /storage/.steam
cat /storage/.local/share/Steam/steamapps/libraryfolders.vdf
```

Missing paths are evidence, not something to create. Resolve every VDF library,
all ancestors, nested mount boundaries and all symlinks in the selected trees.
Record `stat`, filesystem type, UUID, options and free space per physical library.
Use a bounded metadata scan first; a full prefix link scan can be large. Preserve
native logical paths when building a local snapshot (do not dereference aliases
into the investigator's host filesystem). Run the offline planner locally against
that snapshot and review every blocker, including expected Wine `z:` links.

Read installed native `start_steam*.sh`, installer and configuration, and compare
hashes against the pinned source inventory. Read binfmt registrations and host
FEX config without writing them. Inspect `/usr/bin/FEX`, FEXServer, thunks, Steam
client/helper, Proton and pressure-vessel ELF with `readelf -h -l -d -V` locally
on copied files if the device lacks it; do not execute a foreign `ldd` probe.
Record client/runtime/Proton build IDs, Arch graphics_provider.json and recursively
referenced manifests/libraries. Never infer the downloaded builds from package.mk.
Check `vm.max_map_count`, user namespace limits and actual LXC seccomp profile.

Inventory native Steam HOME/XDG settings from launch source or an already-running
process without launching one; avoid collecting the full process environment
because it can contain credentials. Collect paths and ownership for registry,
userdata, custom tools and chosen game saves, not account-token contents. Examine
per-title launch options privately for absolute paths or custom runtime tools.
Determine whether owner0 only, owner1000, mixed ownership, ACLs, or non-POSIX
external filesystems require a different mapping. Document installed state in the
worktree before producing a device adapter; source defaults are insufficient.

## 1. Disposable device storage and runtime qualification

After authorization, keep real Steam stopped and acquire the proposed gate.
Create a dedicated disposable directory on each relevant filesystem. Through a
narrow temporary idmapped LXC mount, as guest1000 create/write/fsync/rename/unlink
files and locks. Check native numeric owner/group and modes, ACL/xattrs, links and
native access before and after. Try owner0/1000/1001/65534 fixture cases separately,
including nested mixed-owner
directories, rename-over and recursive cleanup. Test both immutable-runtime and
updater behavior on disposable trees; do not infer permission from root visibility.
Never chown the installed trees. Remove only the test-owned files/mounts after checking
both tracked cgroups empty. Unsupported idmaps stop shared-write qualification.

The installed Desktop `222bbb4` already includes Xwayland. For a deployable
candidate, reconcile that source dependency explicitly rather than reinstalling
this older task base over it. Check a native X11 client, private Pulse audio,
render-node Vulkan/OpenGL, and a translated minimal x86 program. Then run the
installed Steam runtime's requirement checker and disposable nested bubblewrap
namespace test as guest1000 under the actual LXC policy. Capture stderr, namespace
maps and providers loaded. Do not disable sandboxing or alter host binfmt to pass.
Controller bridging is a separate acceptance gate; desktop keyboard emulation
alone does not pass a controller-game test.

## 2. Backups and first client launch

With both environments stopped, take an offline metadata-preserving snapshot or
verified backup of the entire client/runtime, `.steam`, affected libraries and
all chosen saves/prefixes. Preserve numeric IDs, symlinks, hardlinks, modes,
ACL/xattrs; record hashes/versions and test restoration into a disposable location.
Ensure sufficient free space for rollback plus downloads. Avoid online Cloud
sync during initial rollback-sensitive tests; record its status and unresolved
conflicts. Do not downgrade a prefix simply by switching the Proton executable.

Prepare reviewed exact binds and synthetic home, checking every native absolute
alias from inside LXC before execution. Use guest1000, guest DISPLAY/auth and
private Pulse/Wayland. Launch the existing ARM64 client windowed. Capture startup,
webhelper, pressure-vessel and FEX logs without login secrets. Pass only if existing
account/library state is recognized without creating a second client tree,
existing libraries show installed games, and normal quit drains all child scopes.
A client launch does not pass any game, save or update requirement.

## 3. Games, compatibility tools and saves

Choose small existing titles with recoverable saves: one native Linux title,
one Windows title using the exact existing ARM64 Proton build, and an x86
translation route if actually configured. Record app IDs and selected tools.
Verify correct library, launch, non-software rendering, sound, keyboard/touch,
controller behavior, save creation and loading. Check shader/cache writes and
ownership. Stop fully, launch native ROCKNIX under the same gate, load that exact
save, create progress, quit; return to LXC and verify it. Pass each title separately.
Repeat on each external filesystem; disconnect media only with both sides stopped.

## 4. Updates, exclusion and recovery faults

After a fresh backup, test a small game update; verify manifest/depot version in
both environments. Separately test client self-update/restart and an explicitly
chosen Proton change with a disposable prefix copy. Keep the lease through update
exit 42; verify native can start the resulting client, runtime and prefix. Record
what actually changed. No assumption that any arbitrary Proton downgrade is safe.

Test native-active→LXC reject and LXC-active→native reject, including direct flavor
launchers and ES game shortcuts. Race both supported entrypoints repeatedly;
exactly one may enter preparation, with no shared writes by the loser. Test a game
outliving its client, orphan FEX/wineserver, crashed supervisor, stale marker and
failed detector. Recovery must refuse while any tracked subtree remains populated.
Verify mounts/ACLs are restored on normal exit and supervised fault cleanup.
A direct root binary bypass remains outside cooperative enforcement and must be
stated. Repeat interception checks after a firmware update before allowing use.

## Rollback

Stop both sides; keep exclusion active. Record logs and changed-file inventory.
Only after all relevant process trees are confirmed stopped, remove test-owned
mounts and restore affected client/runtime/config/prefix/save snapshots as one
consistent set. Never restore over running Steam, clear locks by age, delete real
Steam directories, rerun Install Steam as repair, or recursively change ownership.
Restore guest-only aliases/adapters and host hooks from their recorded backups;
leave native files not touched by the test alone. Verify native Steam first,
including library recognition, chosen save and launch. Re-enable Cloud sync only
after reconciling newer remote/local progress. Preserve failure evidence and keep
shared-write Desktop Steam disabled until the failure is understood.
