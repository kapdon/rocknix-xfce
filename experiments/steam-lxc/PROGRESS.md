# Steam LXC local-phase progress

## 2026-10-02 — continuation audit

Previous turn: **progress**. Authoritative state is four clean local commits
through `9ff5c30`, based on LXC `c1a1aec`. The initial report and 14 tests are
present. No device endpoint has been supplied; no RP6 execution is claimed.

The first completion audit found a remaining local task: exclusion depended on
an injected boolean rather than parsing actual cgroup-v2 evidence. Added a
read-only `scope_state.py` POC and nine tests. The reader uses descriptor-relative,
no-follow reads of two trusted scope directories and `cgroup.events` populated
state, including descendants. Missing, malformed, writable or replaced scope
state fails closed. Tests connect it to lease acquisition, release and recovery.

Evidence: `python3 experiments/steam-lxc/test_scope_state.py -v` passes 9 tests.
The kernel definition of populated was checked against
https://docs.kernel.org/admin-guide/cgroup-v2.html on 2026-10-02. Fixtures model
that interface; they do not qualify the RP6 hierarchy or actual kernel behavior.

Remaining local work:

- Audit scope lifecycle against the existing Desktop container ancestor and
  guest cgroup delegation; avoid claiming that a guest-controlled child group
  contains all Steam descendants.
- Review and harden lease recovery file handling, then run all focused tests.
- Update the concise report and final requirement-to-evidence audit.

External gates: actual RP6 installed inventory and ABI closure; native launcher
hook acceptance; device mounts, runtime/graphics/input tests and native round trip.
Read-only inventory needs a current connection target. Writes/launch/deployment
still require explicit authorization. Source defaults cannot settle these gates.

## Continuation results

Completed the remaining local scope/lease tasks above. `EXCLUSION.md` records
why the initial lease must span Desktop startup through complete container
shutdown, rather than relying on a guest-controlled per-app cgroup. A retained
broker parent design avoids treating a collected systemd scope as proof of exit.

Lease review found unsafe recovery path handling and repeated acquire FD loss.
Descriptor-relative state handling, ancestor checks, private regular-file and
hardlink validation, stable lock inode, fsync and repeat-acquire rejection now
have targeted tests. The first combined run failed because the sandbox presents
root-owned `/tmp` as UID65534; the unchanged strict guard passed outside it.
Authoritative result: `python3 -m unittest discover -s experiments/steam-lxc
-p 'test_*.py' -v` passes **29 tests** on ordinary host metadata.

Next: final source/doc review and requirement evidence table; do not equate the
scope reader with installed bidirectional gating. Actual scope provisioning,
installed paths and native hook behavior still require RP6 inventory/access.

Final local review is in `AUDIT.md`. All 29 focused tests pass after adding
nonblocking rejection of FIFO cgroup evidence. Current experiment Python syntax,
local documentation links and repository documentation checks pass. Runtime
payload is unchanged, so the earlier full source-suite result remains scoped to
that same payload; no image build was performed for experimental Python/docs.

The user identified the existing local credential file. It contains username
and password only, with no target address; values were not logged. Read-only
NetBird inventory found no peer named RP6, ROCKNIX or Retroid. Requested only the
missing host/IP or address-file location. No device connection has been made.

## Installed-state continuation

The missing-endpoint blocker above is resolved. Reused a previously verified RP6
SSH helper and the existing local credentials for read-only collection. No device
writes or Steam/game launches occurred; existing Desktop applications were left
running. INSTALLED.md records sanitized evidence; raw private artifacts are not
committed.

Confirmed firmware 9fd38fa / installed Desktop 222bbb4 with Xwayland; actual
Steam client root and two library paths; one library is a bind alias; foreign
UID65534 runtime and UID1001 compatibility-tool content. A uniform root-owner
idmap cannot be claimed to support all updates. Revised design retains foreign
runtime bytes read-only initially with native maintenance as a hypothesis to test.

Fixed static ELF evidence parsing for the device's non-GNU row format. A bounded
96-object candidate walk exhausted its queue with candidates for all parsed
DT_NEEDED names; it is not an actual loader or sandbox test. Three targeted parser
tests bring the focused total to 32. No production runtime changes are justified
before disposable RP6 mapping/runtime tests and a supported native gate.

Final checks: all 32 focused tests pass with ordinary host UID metadata;
repository documentation and whitespace checks pass. The revised report and
requirement audit cover the local-phase deliverables. No runtime payload changed,
so no image build or unchanged upstream suites were run. The next experimental
step requires explicit authorization for stage-1 disposable device tests.
Local-phase completion does not establish Steam support, update safety or native
round trips. No device changes, pushes, publication or merges occurred.
