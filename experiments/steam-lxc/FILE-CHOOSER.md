# LXC file chooser fix and native Steam boundary

## Shipped change

The application rootfs now includes `xdg-desktop-portal` and
`xdg-desktop-portal-gtk`. `rocknix-lxc-session` sets `XDG_CURRENT_DESKTOP=ROCKNIX`
and `GDK_BACKEND=wayland` before `dbus-run-session`, so activated services inherit
the bridged Wayland endpoint. `rocknix-portals.conf` selects GTK. The guest keeps
its existing private session bus and mapped user identity.

The retained-container package procedure is in the
[desktop guide](../../docs/desktop-guide.md#file-chooser). Bootstrap prerequisites
were not expanded: an older retained container is not made unbootable merely
because it lacks these optional application services.

## RP6 verification, 2026-10-02

Applied the two packages and the narrow session/config changes to installed
Desktop `222bbb4`, firmware `9fd38fa`. This was a live incremental repair, not a
replacement of that newer installation with this branch's older base image.

- Guest packages: portal `1.20.3+ds-1`, GTK backend `1.15.3-1`.
- After restarting Desktop, a request as guest UID 1000 activated the frontend
  and returned FileChooser version 4 on the guest session bus.
- A real GTK OpenFile dialog appeared on RP6 through the existing Wayland bridge.
  Selecting the disposable file `chooser-check #1.sh` returned response 0 and
  `file:///storage/games-internal/chooser-check%20%231.sh`.
- Reopening and pressing Cancel returned response 1 with an empty URI list.
- The file was never executed or added to Steam and was removed after testing.
- `bash tests/check.sh` passed. The session regression test additionally checks
  that conflicting inherited desktop/backend values are corrected before bus
  creation. A full application-rootfs image rebuild was not performed.

This verifies file selection and cancellation, not every application's portal
usage, SaveFile, directory selection, or controller-only operation.

## Native ARM64 Steam Browse remains a client limitation

The earlier missing-portal hypothesis was incomplete. A private host-root session
bus, standard portal frontend/GTK backend, and native `/storage` paths were tested
alongside LXC. The native portal could show a dialog from a separate client, but
Steam's Add Non-Steam Game → Browse still failed without calling FileChooser.

The installed Steam client is build **1790377368**. Inspection of its actual loaded
interfaces resolved the fallback file-dialog method to `vgui2_s.so` offset
`0x8c2d0`. The implementation consists of `mov w0, #0; ret`: it returns failure
unconditionally. The caller in `steamui.so` then reports
`failed to retrieve file open dialog results`. No installed client binary was
modified. Removing `-deckard -steamos3` did not change the resolved stub.

Binary SHA256 identities for that finding:

```text
steamui.so  2955808f2dfdc7c46c5d7fe7d9632dd9a124acfca2adc71b6090056c53c7ad0c
vgui2_s.so  de6f7656e7b196302e1e7e76b59a17e1705455b95aade16602da4e9eef68bae5
```

An independent issue was also observed: the bundled SDL 3.5.0 rejects its own
file-dialog API as unsupported. ROCKNIX SDL 3.4.10 cannot override the newer ABI.
A dialog-enabled SDL build at upstream revision
`f068399cabf797b30136753e34f7141c96a6b1e1` successfully used the native portal via
SDL's dynamic API, but **did not repair Steam's separate fallback**. That override
and its build recipe are not shipped as a fix.

The experiment also established that the native portal frontend needs permission
to inspect `/proc/PID/root` for capability-bearing native Steam processes; dropping
all capabilities caused AccessDenied. This is not a reason to grant the LXC guest
host privileges. GTK backend selection follows the standard
[portal configuration](https://flatpak.github.io/xdg-desktop-portal/docs/portals.conf.html),
and the rejected/successful SDL override probes used the documented
[SDL dynamic API](https://wiki.libsdl.org/SDL3/README-dynapi).

Cleanup removed the unused native portal runtime and SDL override from RP6,
stopped all experimental native Steam units, and left no private native portal
directories. Native binfmt handlers were enabled again and ordinary Desktop
remained active. The working guest portal packages/configuration remain installed.
The saved native-gamescope launcher is unchanged; a future native Steam fix needs
a functional client file-dialog implementation or an explicitly designed separate
management workflow, not just another portal package.
