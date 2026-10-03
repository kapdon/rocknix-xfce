# LXC storage reference

The installation separates trusted host integration from persistent Debian
data. See [architecture](architecture.md) and
[Install, Update and Uninstall](upgrades.md) for the active lifecycle.

```text
/storage/rocknix-desktop/
├── managed/
│   ├── host/                   trusted tools and integration
│   │   └── state/              journals, required staging, display preferences
│   └── logs/                   host diagnostics
└── data/
    ├── rootfs/                 Debian, installed packages and accounts
    └── home/                   personal files, settings and app data
```

Only rootfs and home become guest `/` and `/home/rocknix`. The project parent,
`managed/` and all of `data/` are not broad guest mounts. Guest root maps to host
UID/GID 200000; guest rocknix maps to 201000. Preserve all descendant owners and
metadata; never recursively normalize an existing rootfs/home.

Confirmed display choices use
`managed/host/state/display/preferences.json`. The download installer stages
in project-root `install.*` directories and may
retain failed staging. Journals and staged updates are not disposable cache.
Native Tools, boot and service hooks remain at required ROCKNIX paths; transient
mounts/sockets live under `/run`.

## Preservation and backup

Update assembles a fresh component rootfs and replaces the old system, including
packages and accounts/passwords. It preserves `data/home` and shared storage
without copying or changing their ownership. A temporary old rootfs enables
rollback until activation succeeds, then is removed.
Uninstall removes recognized native integration and retains data/tools.
**Install replaces retained data after the overwrite warning**; it does not
reactivate a retained home. Guarded partial state must not be launched or
manually unblocked. See [interrupted operations](upgrades.md#interrupted-operations).

Back up all of `data/` with Desktop, containers and maintenance stopped.
Preserve Linux numeric ownership, modes, hard links, symlinks, ACLs and xattrs;
do not follow links or cross live mounts. Include the display preferences file
if wanted, but do not restore update journals as preferences. Shared
`/storage/{Desktop,Steam,backup,games-internal,games-external}` folders require
independent backups. Offline backup/restore has not been hardware-validated.
External relocation and multiple homes/containers are not supported workflows.

## Implementation

[Path resolver](../payload/bin/rocknix-desktop-paths),
[install](../payload/bin/rocknix-lxc-install),
[update](../payload/bin/rocknix-lxc-upgrade) and
[uninstall](../payload/bin/rocknix-lxc-uninstall) implement trusted-path,
lock and guard checks. Do not clear an active update journal or copy files over
mounted data. See [interrupted operations](upgrades.md#interrupted-operations)
for recovery options.
