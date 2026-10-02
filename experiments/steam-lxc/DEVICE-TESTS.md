# RP6 disposable storage/runtime tests — 2026-10-02

The user authorized disposable LXC testing, then explicitly authorized development
changes on RP6 as a whole. This supersedes the earlier stage-1 permission gate.
The native-preservation objective still applies. No push/publication/merge is
implied. Tests used installed Desktop `222bbb4` and firmware `9fd38fa`, not a new
image from this branch. Native Steam/client/game launches were not performed.

## Reproduced results

[device_stage1.py](device_stage1.py) is the saved, physically executed harness.
It requires `--run-on-rp6-dev`; run through the existing private SSH connection
with script stdin. It stops Desktop, uses the installed supervisor to boot a
maintenance LXC, mounts disposable ext4 fixtures and the existing runtime, and
runs commands as guest UID1000. It does not bind Desktop home or game libraries.
The runtime content is read-only; its `.ref` is overlaid with a **disposable copy**.
It leaves EmulationStation active. After the final run, Desktop was restored
separately and its service reported active; the earlier game was not relaunched.

| Experiment | Observed result |
| --- | --- |
| Existing root-owner idmap, native UID/GID0 fixture | Guest sees UID1000; append/fsync/create/rename/unlink succeed. Backing owner stays 0. |
| Same mapping, native UID/GID1000,1001,65534 fixtures | Guest sees overflow65534; write fails EACCES. Backing owners and file content unchanged. |
| Guest nested user + mount + PID namespace; tmpfs mount | Exit0, `nested-ok`. |
| Shipped srt-bwrap creating a new proc mount | Exit1, `Can't mount proc ... Operation not permitted`. |
| Shipped srt-bwrap reusing existing proc, user namespace | Exit0, `bindproc-ok`. No capability or seccomp changes. |
| pressure-vessel `--test` | Exit0. This alone does not test a runtime. |
| Generic requirement checker | Exit71 with x86 CPU feature diagnostic despite checker being AArch64 ELF. Not sufficient to conclude ARM64 runtime incompatibility. |
| Runtime read-only with ordinary ownership | Fails opening `.ref`: permission denied. |
| Runtime read-only with 65534→201000 mapping | Fails opening `.ref`: read-only filesystem, in both tested copy and no-copy modes. |
| Writable disposable `.ref`, no-copy `files` layout | Fails executing pv-adverb with ENOENT; not a qualified runtime layout. |
| Writable disposable `.ref`, parent runtime directory + copy mode + ARM64 architecture selection | **Exit0 running `/usr/bin/true` inside downloaded runtime.** Reproduced with saved harness. |

The installed `run` source sets `PRESSURE_VESSEL_ARCHITECTURES=aarch64-linux-gnu`,
copy-runtime mode, and the versioned parent directory (which has `usr-mtree.txt.gz`
and `files`). Using only `files` with no-copy does not reproduce that entrypoint.
The successful test uses those layout/architecture choices with disposable scratch
and no graphics provider. It does not disable the runtime's sandbox.

The final successful copy occupied **226,252 KiB (~221 MiB)** in guest `/tmp`.
Pressure-vessel logged 6,008 cross-device-link failures and fell back to copying.
The source and scratch crossed mount boundaries; storage reuse alone does not
make those hardlinks possible. No native `steam-runtime-steamrt-arm64/var` cache
existed at inventory time. This is measured scratch duplication, not another
client/game download, and not a claim that every runtime will have the same cost.

## Consequences for integration

- Root-owned mutable game/client state remains a plausible idmap candidate.
  Mixed-owner runtime/tool updates demonstrably need more than that mapping.
- Read-only runtime bytes alone are insufficient for this pressure-vessel path:
  `.ref` needs writable access, and the packaged runtime needs materialization.
- A disposable lock proves startup only. It does not participate in the native
  lock inode and cannot be promoted as shared-use exclusion. Keep the planned
  host-side whole-Desktop lease and native entrypoint gate as requirements.
- A separate writable runtime cache has now been demonstrated as a fallback.
  Prefer native cache reuse only after it exists and locking/metadata behavior
  are tested; do not promise zero runtime duplication.
- Proc namespace behavior must be tested through actual launch paths. One failed
  new-proc test does not negate the successful pressure-vessel runtime launch.

Automatic approval review rejected a writable idmapped bind of the **real**
`.ref`, citing possible mutation of preserved installation metadata and suggesting
a disposable copy. That rejected action did not execute. The successful test used
that safer alternative. Real shared-lock/update behavior remains untested.

## Cleanup and remaining work

Verified removal of test-owned ext4 fixture directories, mount staging, test
runtime journal, and guest runtime scratch. Native Steam data was mounted only
read-only during these tests. No ownership normalization, installer execution,
client update or native binfmt change was performed. Desktop service was restarted
and reported active; that is service evidence, not a screenshot or UI acceptance.

Remaining acceptance: graphics/audio/input under the actual Desktop session;
protected first client launch and account/library discovery; native gate and
reverse-launch races; per-title saves/Proton; updates and native round trip.
Before shared writes, make a metadata-preserving backup and a concrete scoped
adapter. Expanded device authorization is recorded above; it need not be requested
again for routine RP6 development work. A further automatic-review rejection, if
encountered, must be handled on its own stated merits.

## Real runtime lock follow-up

The user subsequently explicitly approved writable access to the real runtime
lockfile. The saved harness was rerun with `--native-runtime-lock`, keeping all
other runtime content read-only. Both flock and POSIX lockf checks blocked the
guest while held by the host and succeeded after host release. Pressure-vessel
again ran /usr/bin/true successfully. Lockfile inode/device, UID/GID, mode, size,
mtime, SHA256 and xattrs compared equal before/after. This verifies shared-inode
locking and bounded runtime use, not complete native Steam launch coordination.

The explicit approval resolved the earlier rejected operation; that rejection
must not be described as a current permission blocker. The user additionally
requested an actual Satisfactory launch inside LXC, identifying native ROCKNIX
operation as manually verified. See [GAME-TEST.md](GAME-TEST.md) for the partial startup result and pending recovery.
