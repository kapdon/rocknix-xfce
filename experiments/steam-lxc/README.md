# Reusing native ROCKNIX Steam inside Desktop LXC

**Conclusion: credible, conditional reuse; not ready for a production launcher.**
The best path is the existing ARM64 Steam client plus its existing libraries,
Proton and runtimes, presented at the same absolute paths inside LXC. The main
blockers are executable/runtime compatibility and launch coordination, not disk
space. `/storage/Steam` alone does not cover the upstream installation.

Research was recorded before coding in [RESEARCH.md](RESEARCH.md). This branch
is `codex/steam-lxc-reuse`, based on verified remote `dev` at
`c1a1aec8e89b6ddeef3c9b78e58b132be5805599`. The dedicated worktree is
`/home/nexus/.codex/worktrees/4510/rocknix-xfce`. No production code changed.

## Evidence and confidence

- **Current source:** fresh ROCKNIX `next` at
  [`9f8c79dc12c8a49db4d90232c1b9e16b19209ea6`](https://github.com/ROCKNIX/distribution/tree/9f8c79dc12c8a49db4d90232c1b9e16b19209ea6),
  examined installer, launchers, FEX config/package and Steam package. Exact
  paths and the preliminary older checkout are recorded in RESEARCH.md;
  [sources.json](sources.json) records pinned upstream file blob IDs and links.
- **Current project:** LXC maps guest root/user to host200000/201000; temporary
  idmapped binds translate native root-owned shared data for guest1000.
  Private Wayland/Pulse/network/render access already exists. Native FEX plus
  Arch root reuse exists, but does not establish Steam compatibility.
- **Historical evidence:** project docs describe RP6 Desktop and native FEX
  behavior; none establishes Steam-in-LXC or current-device round-trip safety.
  This investigation did not collect or reinterpret old screenshots as proof.
- **Local results:** 14 disposable-fixture/process tests pass. No actual LXC
  mounts, ARM execution, Steam login, game, update, or native round trip tested.
- **Unknown installed state:** firmware, client build, all configured libraries,
  actual symlink targets, native owners, saves and runtime ELF dependencies.
  Source defaults are not a substitute for a device inventory.

## Reuse assessment

“Direct” means the data need not be duplicated; it does not imply it is mounted
or that the software has run successfully in LXC.

| Component | Assessment | Evidence and condition |
| --- | --- | --- |
| Game depots, app manifests, downloads, depotcache | Direct data reuse | All reviewed library trees RW at identical paths; complete pending downloads before switching. |
| ARM64 client, package/beta, client update files | Integration changes | Upstream installs `steamrtarm64/steam`, runtime and `lib/aarch64-linux-gnu` links in the Steam tree. Preserve one update channel/build; resolve Debian ABI closure first. |
| x86 client alternative | Unresolved execution | Native launcher calls `FEX /usr/bin/steam`; needs launcher scripts and translated ELF dependencies beyond mounting games. Prefer ARM64 initially. |
| Downloaded Proton and custom tools | Integration changes | `steamapps/common` and `compatibilitytools.d` reused; upstream installs ARM64 GE/CachyOS. Match architecture and selected version in both environments. |
| Steam Linux Runtime / steamrt3c | Integration changes | Reuse downloaded trees; pressure-vessel still needs functioning nested namespaces, graphics import and paths inside LXC. |
| FEX ArchLinux root | Integration changes | Existing Desktop RO import avoids a second x86 root; native graphics-provider JSON may reference paths not exposed by that import. |
| FEX binaries, thunks, dependencies | Integration changes | Existing FEX/FEXServer/libfmt is a starting point; installed interpreter, DT_NEEDED, symbol versions, thunk manifests and nested runtime translator must be inspected. |
| compatdata / prefixes | Unresolved round trip | Same files and Proton build can be reused; prefix migration, UID/HOME references and Wine links can break return to native. Pin version for first test and snapshot before changes. |
| Shader caches | Direct data reuse, conditional validity | Existing bytes can be shared; different driver/provider builds may invalidate or regenerate them. Do not promise cache hits. |
| config, userdata, login/account state | Integration changes | Steam tree plus `.steam/registry.vdf` and required aliases; retain privacy and avoid collecting account-token contents. Account reuse may still trigger authentication. |
| Saves inside userdata/compatdata | Direct data reuse, validation needed | Back up before either environment writes; verify selected save and Cloud state on both sides. |
| Native Linux saves outside Steam | Unresolved per title | Inventory `.local/share/<game>`, `.config/<game>`, Documents and launch-option paths. Mount only reviewed game directories; no broad native home. |
| FEX config and per-app overrides | Separate adapter state | Read native settings, generate guest-specific paths in guest home; do not let Desktop overwrite host FEX settings. Per-game files inside prefixes remain shared. |
| Session sockets, PIDs, lock files, X11 auth, cgroups | Necessarily separate | Namespace/lifecycle state must belong to the active environment; never reuse live native sockets. |
| gamescope/SteamOS helpers/LSFG | Selective or unresolved | Host DRM gamescope, timezone helper and compositor control are not container dependencies to import wholesale. Optional LSFG needs exact libraries/manifests. |

Minimum added software is a guest X11 path and any missing ARM64 client ABI
libraries, plus small path/provider/launch adapters and host coordination.
Current base lacks X11. The separate `codex/host-library-reuse` branch has guest
Xwayland work (`85e28c8` plus fixes) worth reviewing when integrated into dev.
Do not copy its ongoing checkout or call it deployed. Keep Debian loader/libc;
resolve missing libraries individually rather than mount host `/usr/lib`.
No second client, game library, Proton download or FEX root is inherently
required. Exact additional package count and bytes remain unmeasured.

## Proposed narrow mount/path map

These are **review candidates**, not installable configuration. Stage binds in
the existing private mount namespace; keep the managed host tree outside LXC.

| Native source | Guest path | Access / reason |
| --- | --- | --- |
| Resolved client root, source default `/storage/games-internal/roms/steam` | Same absolute path | RW idmapped; covers client, updates, primary library, Proton, caches and most state. |
| Each resolved `libraryfolders.vdf` library | Same absolute path | RW idmapped, one approved root per library; never mount its disk or `/storage` wholesale. |
| Alias `/storage/.local/share/Steam` | Same alias to client root | Guest-only link under private parent. Also preserve `/storage/Steam` if actually configured. |
| `/storage/roms/steam` or another configured library alias | Same alias or exact bind | Resolve real device mount/symlink first; merged/removable storage can differ. |
| `/storage/.steam` | Same path | RW idmapped after checking every link, including registry, SDK and root aliases; exclude/recreate transient IPC after clean shutdown. |
| Selected game save directories | Original paths under synthetic home | RW idmapped; explicit per-title inventory, not all `.config` or `.local/share`. |
| ArchLinux root, including provider JSON | Existing `/run/rocknix-fex/ArchLinux` plus guest alias at native path if needed | RO nosuid,nodev. Validate every JSON absolute path and required provider dependency. |
| Validated native FEX/provider files | Scoped `/run/rocknix-*` destinations | Individual RO imports; no host loader, native system bus, input directory or DRM primary. |
| Existing Wayland/Pulse/render/network endpoints | Current fixed guest endpoints | Retain project boundaries. |

`HOME=/storage` can preserve native Steam/Wine home references using a **synthetic
container directory**, not a host home bind. Scope HOME and XDG overrides to Steam
and its children; keep Desktop's account/home unchanged. Reproduce only reviewed
Steam aliases and save paths there. Compare native XDG variables first; native
Linux games may consult passwd's `/home/rocknix` despite HOME, requiring a targeted
alias and per-title validation. Never rewrite shared VDF paths to guest-only names.

Native and runtime symlinks must resolve inside the resulting guest topology.
Unmounted external libraries are errors, not invitations to create empty library
folders. Scan nested symlinks and mount points, including custom tools, Proton
prefix `dosdevices`, and graphics JSON; `z:` pointing at `/` should see the
container root and needs explicit review, not an automatic host `/` mount.
Reject guest-controlled path requests; VDF parsing is discovery only. A production
host adapter must use root-controlled approvals, descriptor-based source checks,
mount identity checks and revalidation against symlink substitution races.

Existing Desktop also exposes broader `games-internal` and `games-external`
folders. They can already make data visible, but do not supply `.steam`, aliases,
correct HOME or launch semantics. The proposed Steam-specific map must account
for those existing overlapping mounts; it does not claim Steam has a separate
per-app sandbox or that other Desktop applications cannot touch shared files.

## Runtime and metadata gates

Launch the ARM64 client directly as guest1000 with guest X11 DISPLAY/auth,
existing Pulse server, Wayland runtime and private D-Bus session. Scope the
client's library path and a validated graphics-provider description to that
process tree. Do not blindly apply the generic FEX wrapper's LD_LIBRARY_PATH to
the ARM client. Inspect the installed launcher and helper ELF interpreters,
DT_NEEDED/RPATH and required GLIBC/GLIBCXX versions with `readelf`, then test actual
resolution inside the guest. Never infer execution support from `file` alone.

Retain Sway. Do not invoke `start_steam*.sh`, stop Sway, mutate host binfmt, or
import native root X11 auth. Start with ordinary windowed Steam; qualify gamepad
UI later. An update exit 42 must retain the lease through a bounded restart loop.
FEX execution and native ARM64 Proton are different routes; qualify both as used
by selected games. Host binfmt registrations may contain paths unavailable inside
LXC; investigate actual registrations and translator execution before enabling
x86 paths. Do not “fix” this by granting guest host-global binfmt administration.

[Valve's runtime requirements](https://github.com/ValveSoftware/steam-runtime/blob/master/doc/steamlinuxruntime-known-issues.md)
identify user namespaces as a runtime requirement. LXC startup alone does not
prove nested pressure-vessel/bubblewrap works. Test actual shipped requirement
checkers and nested mounts/seccomp as guest1000, including provider and Pulse
visibility. Keep browser/runtime sandboxes enabled. The current LXC seccomp
profile, namespace limits and firmware kernel must be tested together.

Desktop controller-to-keyboard navigation is not gamepad passthrough. Raw input
is deliberately excluded. Keyboard/mouse games may work through Xwayland;
controller games need a reviewed userspace bridge or narrowly defined virtual
controller interface, with hotplug/Steam Input validation. A requirement for broad
`/dev/input`, host IPC or privileged gamescope is a stop condition, not a default.

[Idmapped mounts](https://docs.kernel.org/filesystems/idmappings.html) translate
ownership at the mount without recursively changing backing-file ownership.
For native root-owned data, reuse the project's 0→201000 mapping so guest1000
writes remain native UID/GID0. Verify creates, renames, lock files and modes on
the actual filesystem. Native1000 and mixed ownership need distinct approved
mapping/ACL designs; a single mapping cannot collapse two native owners into
one guest owner while preserving both. Fail closed instead of chown/chmod -R.
Check filesystem idmap support, ACL/xattrs, mount options, hardlinks, free space
and removable-media behavior. Fixture metadata preservation is not an idmap test.
Shared executables/config will later be consumed by native Steam, often as root:
sharing deliberately carries those changes across environments; nosuid alone
does not create a trust boundary for shared scripts or compatibility tools.

## Exclusive-use lifecycle and limits

1. A trusted host broker acquires one persistent-inode flock before either
   launch's preparation, file writes or namespace setup. It checks native
   `steam-bigpicture.scope` and the Desktop Steam cgroup, plus unknown Steam
   process trees. Reject with “Close Steam in ROCKNIX/Desktop first.” Unknown or
   failed inspection blocks launch. Do not use `pgrep steam` as the authority.
2. Put all children in host-owned tracked cgroups before exec. Retain the lock
   in a supervisor, not just the initial client PID. Keep a host-only active
   marker; also coordinate Desktop install/update/uninstall and Steam installers.
3. All native entrypoints, including direct flavor launchers, ES game shortcuts,
   restart paths and manual supported commands, must use the same broker. Native
   firmware scripts currently do not. A systemd scope check alone has a race;
   a service ordering rule does not cover direct binaries. Pause ES is helpful
   but insufficient. Firmware updates must revalidate any hook.
4. On normal exit, wait for the full cgroup subtree (games, wineserver, FEXServer,
   browser helpers, updater) to empty. Then remove staged resources and active
   marker and release the lock. Keep exclusion throughout exit-42 restarts.
5. If supervisor dies, flock may release while children survive. The marker
   therefore blocks subsequent launches. Recovery must inspect both cgroups,
   terminate only owned work if separately authorized, verify emptiness, finish
   unmount/ACL cleanup, then clear marker. Never trust a recycled PID or age.
   Reboot recovery checks persisted markers and data consistency before clearing.

Without native cooperation we can reject an already-running native session and
serialize container launches, but **cannot guarantee reverse exclusion or race
freedom**. Direct root launches can bypass any cooperative lock. Default to
unavailable shared-write Steam until supported native entrypoints are gated;
an explicitly supervised hardware experiment is narrower than production safety.
The lock also cannot prevent another app editing already-shared directories.

## Local artifacts, checks and next steps

- [discovery.py](discovery.py): read-only offline snapshot resolver, strict VDF
  subset, library/alias review plan and symlink escape reporting. No mount or
  launch commands. Requires explicit exact resolved root approvals, retains
  spaces and detects ambiguity. Unsupported VDF syntax fails explicitly.
- [lease.py](lease.py): cooperating-supervisor flock/marker model. Its scope
  detector is injected, **not implemented against RP6 systemd/proc/cgroups**.
  Recovery is a model operation, not a device cleanup utility.
- [test_poc.py](test_poc.py): 14 tests including two independent competing Python
  processes, a killed winner, retained crash marker, simulated surviving child
  scope, VDF errors, missing libraries, cycles, external links and unchanged
  fixture data/metadata (excluding read access times).

Validation on 2026-10-02: all 14 POC tests, `python3 tests/docs.py`, and
`bash tests/check.sh` passed. The full source suite initially hit the sandbox
Unix-socket restriction in `tests/lxc-session.py`; its unrestricted local rerun
passed. `git diff --check` passed. No upstream test suites or device tests ran.

Run `python3 experiments/steam-lxc/test_poc.py -v` locally. The planner CLI is:
`python3 experiments/steam-lxc/discovery.py --snapshot SNAPSHOT --approve-root /storage/games-internal/roms/steam --approve-root /storage/.steam`.
Add reviewed external roots explicitly; output is untrusted review JSON, never
input for root mount execution. It does not enumerate saves outside those trees,
validate ELF dependencies, preserve snapshot-copy ownership automatically, or
handle concurrent mutation. It deliberately refuses the live host root `/`.

No full image build is warranted for experiment-only files; no runtime payload
changed. No hardware-operation milestone is passed. Follow [VALIDATION.md](VALIDATION.md)
for exact staged collection, acceptance and recovery. If shared client updates or
prefix round trips fail, fall back to a separate small client/home and share
compatible depots only, with separate per-environment prefixes/caches as needed.
If nested runtimes or controller access require unacceptable boundary expansion,
keep native Steam as the launch route; file visibility remains useful but is not
Steam-in-LXC support.
