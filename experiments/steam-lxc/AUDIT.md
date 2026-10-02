# Requirement audit — 2026-10-02

The local investigation is not end-to-end Steam support. This table audits the
original request without treating green fixtures as hardware evidence.

| Requirement | Current authoritative evidence | Status / next action |
| --- | --- | --- |
| Dedicated worktree, correct LXC base, preserve other work | Branch `codex/steam-lxc-reuse`; `RESEARCH.md` records fetch/base `c1a1aec`; changes restricted to `experiments/steam-lxc` | Established locally; no primary-checkout edits, pushes or publication. |
| Research before POC | Initial research checkpoint saved before discovery/lease code; pinned `sources.json` and local commit sequence | Established for source-level findings. |
| Exact upstream source and launch/dependency map | Installer, three launch scripts, FEX config/package and Steam package pinned by commit/blob; README assessment | Source evidence established; installed revisions and static ABI candidates now recorded in INSTALLED.md; actual loader/runtime behavior unverified. |
| Maximum practical component reuse | README table covers client, all library data, tools, runtimes, prefixes, caches, config/account state, saves and FEX | Conditional design established; per-title/installed compatibility unresolved. |
| Narrow storage paths and links | `discovery.py`, discovery fixtures, README path map | Offline behavior tested; current two-library alias topology inventoried; nested links and future removable filesystems remain gates. |
| Preserve UID/GID and metadata | Existing LXC idmap implementation inspected; no real data writes; fixture no-mutation checks | Actual mixed owners established; ACLs, hardlinks and filesystem idmap behavior remain unverified. No chown workaround proposed. |
| CPU/graphics/audio/input/nested runtime | Source map identifies native ARM64 client, FEX route, provider JSON, private endpoints, missing base X11, installed Xwayland and controller gap | Concrete integration requirements recorded; static ABI candidates inventoried; runtime loading, pressure-vessel and Steam behavior not established. |
| Host/container exclusion, races, crashes, children | `lease.py`, `scope_state.py`, 19 exclusion/file/cgroup tests within 32 total; `EXCLUSION.md` | Local mechanisms tested; full Desktop lifetime chosen for host containment. Native interception, retained scope provisioning and cleanup adapter not implemented. |
| Local POCs and justified implementation | Discovery planner, cgroup evidence reader, hardened lease, all fixture/process tests | 32 focused tests pass. Installed mixed-owner/update and native-gating risks preclude a production entrypoint. |
| Relevant build/testing | Initial full `tests/check.sh` passed; current 32 POC tests and docs checks passed; whitespace checks | No image/package build needed: changes are experiment/docs only, not in runtime payload. No claim of ARM execution. |
| Staged RP6 validation/recovery | `VALIDATION.md` stages 0–4, per-title criteria and rollback; `EXCLUSION.md` adds containment gate | Read-only stage 0 partly executed; stages 1–4 require separate authorization. |
| Final review, limitations, exact next steps | This audit, `PROGRESS.md`, README limitations and fallback | Reviewed current sources/tests; local deliverables reviewed with installed evidence; hardware qualification remains outstanding. |

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

## Current boundary and exact next action

Existing credentials and a previously verified SSH connection enabled read-only
RP6 inventory. The earlier missing-endpoint blocker is resolved. INSTALLED.md
records the installed firmware/Desktop revisions, library aliases, mixed owners,
static ABI candidates and active container ancestor. Raw inventory stays private.

A production launcher is not justified by file discovery: native interception is
absent, mixed-owner runtime/tool updates cannot be promised by one idmap, and
nested runtime execution is untested. The local POCs establish parsing and
coordination primitives only. No runtime payload changed or image build is needed.

Next, request stage-1 authorization for disposable device ownership/idmap and
runtime-namespace qualification, scheduled when the active Desktop work can be
stopped. Do not touch real Steam data or launch Steam/games under that permission.
After those results, finish the specific native-gate/mount adapter locally before
seeking stage-2 backed-up client-launch authorization. Per-title saves, updates
and native round trips remain separate acceptance gates, with rollback in
VALIDATION.md. No pushes, publication or merges are authorized.
