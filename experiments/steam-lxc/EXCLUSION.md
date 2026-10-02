# Host exclusion integration contract

This refines the report's proposed lifecycle after auditing
`payload/bin/rocknix-lxc` at `c1a1aec`. It is not an installed launcher.

## Containment and lifetime

Desktop's existing host-owned cgroup is
`/sys/fs/cgroup/unified/<runtime.name>` (default `rocknix-lxc`), not a systemd
`desktop-steam.scope`. The LXC init and attached processes live in descendants.
The guest systemd tree is delegated inside that ancestor. Observing only a
Steam child cgroup would miss a process migrated to another guest cgroup; parent
PID exit, reparenting or an empty top-level `cgroup.procs` is not enough.

Initial integration must acquire the common lease **before Desktop exposes the
shared Steam trees**, and retain it for the entire Desktop runtime. Native
Steam is refused while that Desktop session exists, even if its Steam UI has
closed. This conservative lifetime matches the existing shared-data/container
boundary and preserves all child processes under the observed host ancestor.
It does not require another Steam installation or a privileged guest. Reducing
exclusion to individual apps would require new containment design and evidence.

The existing runtime removes its cgroup during cleanup. The broker therefore
must observe `populated=0`, finish mount/ACL cleanup and journal completion
before allowing deletion/release, or retain an outer host-owned broker parent
through cleanup. Do not query a vanished path and infer emptiness. `ScopeSet`
intentionally treats missing paths as unknown. The integration needs two retained
parent scopes (native and Desktop), created and validated by the trusted broker;
`steam-bigpicture.scope` becomes a native descendant or remains an additional
observation. No such parents are created by this POC.

For native launch, the lease must precede `source /etc/profile`, `set_kill`, VDF
edits and binfmt changes, not merely surround the final `systemd-run`. A single
broker wrapper must cover the dispatcher, both flavor entrypoints, ES game
shortcuts, installer/uninstaller and supported maintenance commands. The native
scope re-exec must pass through an authenticated broker-owned continuation;
checking `_STEAM_SCOPE=1` alone is not authorization to bypass the gate. Never
inherit a lease FD through Steam/FEX/webhelper: the broker owns it and tracks
cgroup lifetime. Account for exit-42 restart without releasing the lease.

Keep Desktop's existing runtime/image maintenance lock, with a fixed order:
installation/maintenance lock first, then common Steam lease, then temporary
mount/ACL resources. Native operations requiring both follow the same order;
ordinary native Steam uses only its Steam lease. Never wait on a second lock
while holding it in inverse order. Separate native Steam installer interception
is needed because it changes runtimes/FEX data even without launching Steam.

## Authority and state

- Host-owned broker config supplies exact approved roots, unit/cgroup identities
  and fixed argv. Guest/VDF paths and environment variables are not authority.
- Fixed Desktop start requests may use the existing narrow control architecture;
  no arbitrary command execution or caller-specified host path is added.
- Start checks include pre-existing native scope and recognized process trees.
  Name/executable checks are diagnostic backstops; renamed executables, scripts,
  custom launchers and manual root commands mean they cannot prove absence alone.
- Cooperative interception plus host containment is required for race exclusion.
  A root user can deliberately bypass it. Firmware replacing launchers must
  disable integration until the hook/version contract is revalidated.
- Post-crash marker clearance needs cgroup evidence **and** completed resource
  cleanup. `Lease.recover` only tests the supplied emptiness callback; it does
  not repair mounts/ACLs and must not be exposed as a standalone device command.
- Boot ID and a journaled generation must bind retained runtime state to the
  broker session. After reboot no process survives, but incomplete downloads,
  filesystem state and abandoned resource journals still require inspection.

## Implemented local evidence

`scope_state.py` reads two configured existing scopes relative to directory file
descriptors, rejects symlink components and writable/unowned evidence, parses
`cgroup.events`, and double-samples inode identity/population. The kernel's
[populated definition](https://docs.kernel.org/admin-guide/cgroup-v2.html#un-populated-notification)
includes descendants; the POC never substitutes an empty direct PID list.
Replacement or read failure is unknown. Double sampling is not atomic and does
not close an uncooperative launch race. The caller must verify the real cgroup2
mount and its host-controlled ancestors, names and delegation boundary first.

`lease.py` holds a persistent-inode flock, uses descriptor-relative private
state, rejects symlink/hardlink/FIFO lock files, fsyncs marker and parent, and
retains the marker after a supervisor crash. Reacquiring an already-held lease
raises without losing the original FD. Every release/recovery checks scope
state under the same lock. Power-loss durability and RP6 filesystem behavior
are not established by these tests.

29 local tests cover path discovery, two-process competition, killed supervisor,
simulated populated descendants, changing/malformed/missing cgroup state and
unsafe state-file objects. They establish userspace behavior on disposable
fixtures only. Real hierarchy setup, native wrapper installation, mount cleanup,
firmware update hooks and device process attribution remain unimplemented
pending the installed RP6 inventory and an authorized hardware experiment.
