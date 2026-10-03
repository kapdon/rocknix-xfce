# ROCKNIX Desktop

A handheld-first Sway desktop with native Wayland apps in a Debian 13 ARM64
LXC container. Open **Tools → Desktop Mode**; **Exit Desktop** closes apps and
returns to ROCKNIX. Save your work before exiting.

> **Disclaimer:** ROCKNIX Desktop is an independent project and is not affiliated
> with, endorsed by, or maintained by the [ROCKNIX project](https://rocknix.org/).

## Desktop preview

Actual screens captured on the Retroid Pocket 6.
[Install or update](#install-or-update) · [Controller keybinds](#apps-and-controls)

| Apps at a tap | A keyboard when you need it |
| --- | --- |
| ![Apps launcher with Firefox, Files and Foot favorites](docs/media/apps.png) | ![Four-row on-screen keyboard filtering Apps with the text fil](docs/media/keyboard.png) |
| Tap **Apps**, choose with the **D-pad**, then confirm with the **bottom face button**. | **L3** shows or hides the keyboard. Tap **123** for numbers and symbols, or **ABC** to return. |

| Desktop settings | Resolution and fractional scaling |
| --- | --- |
| ![Settings menu with audio, network, display and window-layout options](docs/media/settings.png) | ![Display settings showing default 1.0 scaling and resolution controls](docs/media/display.png) |
| Tap **Settings** for audio, network, display and window-layout options. | Choose scaling or an advertised resolution/refresh rate. Unconfirmed changes revert automatically. |

[Screenshot guide](docs/media/README.md) ·
[View this gallery on GitHub](https://github.com/kapdon/rocknix-desktop/tree/dev#desktop-preview)

## Supported devices

Only the **Retroid Pocket 6** has been tested. Other ROCKNIX devices in the
**SM8550/QCS8550 family** are experimental and require confirmation before
installation. Blank cells indicate untested devices. Other chipsets are
currently out of scope.

| Device | ROCKNIX build | Tested |
| --- | --- | --- |
| Retroid Pocket 6 | 20260930 nightly (`9fd38fa`, next) | Yes |
| Retroid Pocket 6 (top D-pad) | | |
| Retroid Pocket Nova | | |
| AYN Odin 2 | | |
| AYN Odin 2 Portal | | |
| AYN Odin 2 Mini | | |
| AYN Thor | | |
| AYANEO Pocket ACE | | |
| AYANEO Pocket DMG | | |
| AYANEO Pocket EVO | | |
| AYANEO Pocket DS | | |
| AYANEO Pocket S Mini | | |
| AYANEO Pocket S (2K) | | |
| AYANEO Pocket S (1K) | | |

Device eligibility follows the
[ROCKNIX SM8550 inventory](https://github.com/ROCKNIX/distribution/blob/a55d58a1209b35e287dd55a3aad67a5543b467ce/projects/ROCKNIX/config.xml).
See the [device requirements](docs/devices.md) for checks
and how to report results.

## Install or update

Back up saves and settings, exit Desktop, and leave EmulationStation running.
From a computer, connect to the device over SSH with `ssh root@DEVICE_IP`
(replace `DEVICE_IP` with its network address). Run the commands below **in that
SSH session on the ROCKNIX device**, not in your computer's local terminal.

The device needs Internet access, at least **4 GiB free
on /storage**, and **10% main-device battery**. Charging does not bypass the threshold.

```sh
curl -fsSL https://raw.githubusercontent.com/kapdon/rocknix-desktop/dev/install.sh | bash
```

This command selects the latest published stable version. To select a specific
version, use the same installer and add `--release TAG`, for example:

```sh
curl -fsSL https://raw.githubusercontent.com/kapdon/rocknix-desktop/dev/install.sh | bash -s -- --release v0.1.0
```

For the rolling development build, add `--dev`:

```sh
curl -fsSL https://raw.githubusercontent.com/kapdon/rocknix-desktop/dev/install.sh | bash -s -- --dev
```

Choose either `--dev` or `--release TAG`; they cannot be combined.
Available versions are on the
[releases page](https://github.com/kapdon/rocknix-desktop/releases).

On eligible non-RP6 devices, the installer asks whether to proceed on untested
hardware before downloading the bundle or changing storage. **No** is the
default. The warning appears on every Install/Update invocation, and `--yes`
cannot bypass it. Eligibility does not establish hardware support.

The installer displays installed/available revisions and asks before proceeding.
**Update replaces the container system and installed packages while preserving
home, user settings and shared files. Install replaces Desktop-owned apps,
home and settings without a recovery copy**, including retained data after
Uninstall. `--yes` accepts the selected operation, including this deletion;
the untested-device warning still requires an answer.
`--update` requires a healthy existing install; `--install` selects replacement.
`--check` checks device prerequisites only. Installation leaves native boot and
EmulationStation active. Refresh the game list if the Tools entry is missing.

The installer creates and validates its storage directories. These commands
read confirmations from the terminal, not the piped script. Without a terminal,
required confirmations cancel the operation; `--yes` never bypasses the
untested-device warning. To inspect the script first, run just `curl -fsSL URL`,
using the same installer URL. Bundle downloads are checksum-verified; checksums
establish integrity, not independent trust.
**About Desktop Mode** in Apps or `rocknix-version` in Foot shows the installed
commit/build date.

## Apps and controls

Tap **Apps** for Firefox, Files, Foot and other installed apps; type to filter.
Tap a row, or select with D-pad and confirm with the bottom face button.
Waybar provides **Settings**, **Keyboard**, battery, clock and **Exit Desktop**;
**Windows** appears with multiple apps. Touch uses ordinary app controls and
the on-screen keyboard. Network settings may require hiding the keyboard to
reach Save/Cancel.

| Control | Action |
| --- | --- |
| D-pad | Navigate launcher choices and app controls |
| Bottom face button | Confirm / Enter |
| Right face button or Start | Back / Escape |
| Left face button (West) | Next field / Tab |
| Top face button (North) | Previous field / Shift+Tab |
| Select | Cycle open windows |
| L3 | Show/hide the keyboard |
| R3 | Request a normal close of the focused window |
| Bumpers / triggers | Scroll / pointer clicks |

Positions apply regardless of printed button labels. Tap and release North:
holding it also holds Shift. Apps determine their own field order.
See the [complete controller mapping](payload/input/desktop.yaml).

R3 does not force-kill an app and does not repeat while held, but an app can close
without a save warning. Closing the last app leaves the panel available.
**Exit Desktop** has a confirmation with Cancel selected initially. It closes
desktop apps and shuts down the desktop runtime before returning to ROCKNIX;
it does not keep apps running in the background. Save your work before exiting.

The bundled keyboard does not replace the native ROCKNIX keyboard. **123** opens
symbols; **ABC** returns to letters. One tabbed workspace is the default;
settings utilities and Firefox Picture-in-Picture float when space allows.
**Settings → Display settings** previews resolution/scaling for 15 seconds;
Keep saves the choice, and exit restores the host display. Desktop defaults to 1.0×.
See the [desktop guide](docs/desktop-guide.md) for keyboard and window details.

Desktop apps share one unprivileged container. Guest user/sudo password is
`rocknix` / `rocknix`; change it with `passwd`. System replacement updates reset this password.
Container sudo cannot become native host root. See [architecture](docs/architecture.md).

## Storage and backup

All persistent ROCKNIX Desktop project data lives under
**`/storage/rocknix-desktop/`**. The layout separates personal and Debian data
from project-managed host files:

```text
/storage/rocknix-desktop/
├── managed/
│   ├── host/
│   │   ├── bin/                trusted launch and maintenance helpers
│   │   ├── input/              controller mappings
│   │   ├── integration/        native launcher and boot-hook sources
│   │   ├── host-tools/         bundled host binaries and libraries
│   │   └── state/              device consent, journals and update staging
│   │       └── display/
│   │           └── preferences.json  confirmed resolution/scaling choices
│   └── logs/                   session diagnostics
├── data/
│   ├── rootfs/                 Debian, installed apps and accounts
│   └── home/                   personal files, app profiles and settings
└── install.*/                  installer downloads/staging, when present
```

`data/rootfs/` becomes the container's `/`, including installed packages,
passwords and system settings. `data/home/` becomes `/home/rocknix`.
Update replaces rootfs and preserves home. Install replaces both after the overwrite warning.
The helpers and dependencies in `managed/host/` are refreshed by Update.
Its `state/` also holds persistent display preferences and operation guards;
do not delete active journals, staging or guards. Failed installer staging may
remain in `install.*` directories for recovery.

Back up **all of `data/`** while Desktop, containers and maintenance are stopped,
preserving numeric owners, permissions, links, ACLs and extended attributes.
Guest root maps to host UID/GID 200000; guest `rocknix` maps to 201000.
Copying home alone omits apps/accounts. Include
`managed/host/state/display/preferences.json` if you want saved display choices.
Offline backup/restore has not been hardware-validated.

The five shared folders (`Desktop`, `Steam`, `backup`, `games-internal`,
`games-external`) remain directly under `/storage`, outside this project tree.
They are mounted individually for Desktop apps and need separate backups;
`/storage/Desktop` keeps its native name. Small native Tools, boot and service
hooks remain at ROCKNIX's required paths; transient mounts and sockets live
under `/run`. See the [storage reference](docs/storage.md).

Exit Desktop before uninstalling, then run the installer with `--uninstall`
in a root SSH session on the ROCKNIX device:

```sh
curl -fsSL https://raw.githubusercontent.com/kapdon/rocknix-desktop/dev/install.sh | bash -s -- --uninstall
```

The same script handles every operation: add `--update`, `--install`, or
`--uninstall` after `bash -s --`. Add `--check` for a non-mutating check.
Uninstall uses the installed trusted helper without downloading a bundle;
no second public script is needed. It removes native integration and retains
Desktop data/tools. A later Install replaces the retained data. For interrupted
operations, keep the downloaded bundle and journals; do not clear guards
manually. See
[Install, Update and Uninstall](docs/upgrades.md) for behavior and recovery limits.

## Technical references

[Build](docs/build.md) · [Contribute](contributor.md) ·
[Architecture and dependencies](docs/architecture.md)

Suspend/resume and compatibility with future ROCKNIX updates are untested.
