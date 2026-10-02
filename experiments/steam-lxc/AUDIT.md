# Requirement audit — 2026-10-02

The local investigation is not end-to-end Steam support. This table audits the
original request without treating green fixtures as hardware evidence.

| Requirement | Current authoritative evidence | Status / next action |
| --- | --- | --- |
| Dedicated worktree, correct LXC base, preserve other work | Branch `codex/steam-lxc-reuse`; `RESEARCH.md` records fetch/base `c1a1aec`; changes restricted to `experiments/steam-lxc` | Established locally; no primary-checkout edits, pushes or publication. |
| Research before POC | Initial research checkpoint saved before discovery/lease code; pinned `sources.json` and local commit sequence | Established for source-level findings. |
| Exact upstream source and launch/dependency map | Installer, three launch scripts, FEX config/package and Steam package pinned by commit/blob; README assessment | Source evidence established; installed RP6 versions, ELF closure and external libraries unknown. |
| Maximum practical component reuse | README table covers client, all library data, tools, runtimes, prefixes, caches, config/account state, saves and FEX | Conditional design established; per-title/installed compatibility unresolved. |
| Narrow storage paths and links | `discovery.py`, discovery fixtures, README path map | Offline behavior tested; actual topology, removable filesystems and native symlink targets require inventory. |
| Preserve UID/GID and metadata | Existing LXC idmap implementation inspected; no real data writes; fixture no-mutation checks | Actual mixed owners, ACLs, hardlinks and filesystem idmap behavior unverified. No chown workaround proposed. |
| CPU/graphics/audio/input/nested runtime | Source map identifies native ARM64 client, FEX route, provider JSON, private endpoints, missing base X11 and controller gap | Concrete integration requirements recorded; installed ABI, pressure-vessel and RP6 behavior not established. |
| Host/container exclusion, races, crashes, children | `lease.py`, `scope_state.py`, 19 exclusion/file/cgroup tests within 29 total; `EXCLUSION.md` | Local mechanisms tested; full Desktop lifetime chosen for host containment. Native interception, retained scope provisioning and cleanup adapter not implemented. |
| Local POCs and justified implementation | Discovery planner, cgroup evidence reader, hardened lease, all fixture/process tests | 29 focused tests pass. No production entrypoint or mount mutation justified without installed inventory. |
| Relevant build/testing | Initial full `tests/check.sh` passed; current 29 POC tests and docs checks passed; whitespace checks | No image/package build needed: changes are experiment/docs only, not in runtime payload. No claim of ARM execution. |
| Staged RP6 validation/recovery | `VALIDATION.md` stages 0–4, per-title criteria and rollback; `EXCLUSION.md` adds containment gate | Plan prepared; no device stages executed. |
| Final review, limitations, exact next steps | This audit, `PROGRESS.md`, README limitations and fallback | Reviewed current sources/tests; installed-state portion remains incomplete. Goal remains active. |

## Review findings addressed

- The original lease relied only on a boolean callback. A cgroup-v2 reader now
  parses real interface syntax and fails closed on absent, malformed, replaced,
  writable or symlinked evidence; a FIFO cannot block the reader.
- Recovery previously lacked the acquisition path checks. All operations now use
  private descriptor-relative state; lock hardlinks/FIFOs/symlinks are refused.
- Repeated acquire could replace/leak the held FD. It now rejects re-entry while
  retaining the original lock, verified by a competing acquisition.
- A per-app guest cgroup was not sufficient host containment. The initial lease
  now spans the complete Desktop container, before shared mounts through cleanup.
- `cgroup.events` descendant population is used, not direct `cgroup.procs` alone.
  Missing collected scopes block recovery instead of being treated as empty.

## Precise external dependency and attempted alternatives

The user supplied the location of existing credentials; that file has no host
address. Read-only NetBird inventory has no RP6/ROCKNIX/Retroid-named peer. No
current RP6 endpoint or offline installed inventory is identified yet. A fresh pinned upstream source checkout, current project source,
separate Xwayland branch inspection, offline symlink/VDF fixtures and independent
process/cgroup-interface tests provided useful local evidence but cannot identify
the user's current downloaded binaries, library topology, ownership or saves.
No credential guessing, device launch, Steam-data writes or deployment occurred.

Minimum next input: current RP6 SSH host/user/port using existing authorized
credentials, or a private offline inventory path. Read-only stage 0 can then
settle installed-state questions and justify a specific local integration patch.
Do not request device-write approval merely to collect that inventory. After the
adapter is concrete and locally tested, request authorization for the exact
stage-1 disposable device tests and subsequent backed-up Steam experiments.
