# Install, update and uninstall

## Release selection

The default installer selects the latest published stable version. Add `--dev`
for rolling development, or `--release TAG` for a specific version. These
selection flags cannot be combined. See the [installation commands](../README.md#install-or-update).

| Operation | Effect |
| --- | --- |
| Install | Replaces Desktop applications, home and settings after an explicit overwrite warning |
| Update | Replaces the container system and packages from components; preserves home and shared storage |
| Uninstall | Removes native launch integration; retains Desktop data and trusted tools |

Shared ROCKNIX storage and native ROCKNIX accounts are outside these operations.

## Install and Update

Exit Desktop and leave native ROCKNIX running. Installation requires at least
4 GiB free on `/storage` and 10% main-device battery. Update also checks space
for the complete candidate system and temporary host backup before activation.
Other eligible [SM8550 devices](devices.md) receive a default-No untested-device
warning. `--yes` and charging do not bypass device eligibility or battery checks.

The installer downloads checksum-verified components and assembles a complete
new container. A healthy existing LXC installation defaults to Update, including
installations originally made from a monolithic export. Updates require a new
component release manifest; a legacy export cannot serve as an update candidate.

Update preserves `data/home` in place: no recursive ownership changes or copying.
It also preserves shared Steam/game storage and host display/provider preferences.
The old `data/rootfs` is replaced, including extra APT packages, system edits,
accounts and passwords. Reinstall extra system packages afterwards. Apps stored
in home/shared storage remain, but may require dependencies to be reinstalled.
The new guest account uses the image's documented default password.

Before switching, the candidate boots in a mapped maintenance container with no
home/shared mounts. Guest code runs as mapped container root, never native root.
After successful host activation/preflight, the updater removes the previous
rootfs and temporary backup. It does not perform APT transactions or merge local
system edits into the old container.

- `--install` explicitly replaces Desktop applications **and home**.
- `--update` requires an existing installation suitable for Update.
- `--yes` accepts the selected operation, including home deletion for Install.
- `--check` on the downloader checks device prerequisites without downloading.
  The assembled `upgrade.sh --check` additionally verifies the component candidate
  and mapped-ownership eligibility without switching installed data.
- An unchanged revision and manifest checksum is a no-op for Update.
- Selecting an older component release replaces the system with that release's
  package versions; it does not downgrade or migrate user application data.

SHA-256 establishes integrity, not publisher trust. Components contain privileged
host code; use trusted project releases.

## Uninstall

Exit Desktop and run:

```sh
curl -fsSL https://raw.githubusercontent.com/kapdon/rocknix-desktop/dev/install.sh | bash -s -- --uninstall --check
curl -fsSL https://raw.githubusercontent.com/kapdon/rocknix-desktop/dev/install.sh | bash -s -- --uninstall
```

Uninstall removes recognized service, boot and Tools integration. It keeps
`data/rootfs`, `data/home` and trusted tools. A later explicit **Install replaces
those retained trees**, including home.

## Interrupted operations

Keep the downloaded manifest, components, staging directories and journal.
Do not clear guards or manually start Desktop against a partial update.

An interrupted replacement is bound to the original manifest checksum. Repeat
that update: the updater restores the previous rootfs and host integration before
retrying, or finishes cleanup if activation was already committed. The ordinary
installer routes a guarded update to recovery instead of offering home deletion.
If the selected release changed, use the original staged `upgrade.sh` with
`--bundle ORIGINAL-MANIFEST --sha256 ORIGINAL-HASH --yes`.

A normal activation failure rolls back. A failed cleanup or rollback keeps the
journal and blocks Desktop until recovery completes. Live mounts, changed file
identities or unsafe paths are errors, not permission to delete unrelated data.
Filesystem interruption tests cover switch boundaries; physical power-loss
behavior still requires device qualification.

## Persistence and backups

Keep independent backups while Desktop and maintenance containers are stopped.
Preserve `data/home` with numeric ownership, modes, links, ACLs and extended
attributes, and shared storage separately. Save rootfs only if you need its old
packages/system customizations. Host display preferences live in
`managed/host/state/display/preferences.json`; do not restore active journals as
preferences. Offline backup/restore has not been hardware-tested.
