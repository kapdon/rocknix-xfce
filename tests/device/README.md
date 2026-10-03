# RP6 checks

These checks exercise an installed candidate on an exclusively reserved RP6.
They are separate from `bash tests/check.sh`. Copy this directory to the device
and run the host checks as native root from that directory. Install the same
candidate revision first, record its bundle checksum and installed `build-info`,
and keep each command's output with that identity.

| Check | Invocation on the RP6 | Scope |
| --- | --- | --- |
| Boundary | `python3 check-installed-boundary.py` | Active Desktop; mapped identities cannot write host controls; narrow guest mounts |
| Task ceilings | `python3 check-installed-limits.py` | Active Desktop; bounded 16-task child service, outer controls and production limits |
| Memory accounting | `python3 check-installed-memory.py` | Idle active Desktop below 512 MiB; allocate/release 128 MiB without exhausting the container |
| Low storage | `python3 check-installed-space-failure.py` | Private 4 MiB tmpfs; ENOSPC leaves previous files intact and permits retry |
| Guest APT | `python3 check-package-upgrade.py` | Active Desktop; authenticated installation/upgrade/removal of disposable packages |
| Guest dpkg interruption | `python3 check-package-interruption.py` | Active Desktop; interrupt/configure/remove one disposable dependency-free package |
| Session recovery | `python3 check-component-recovery.py COMPONENT` | Active Desktop; `COMPONENT` is `waybar`, `wvkbd-rocknix`, `startup`, `stop`, `supervisor` or `guest-init` |
| Init refusal | `python3 check-init-recovery.py` | Close Desktop; temporarily deny verified guest init execution, restore its exact inode/mode |
| Preflight refusal | `python3 check-preflight-recovery.py` | Close Desktop; exclusive temporary update guard; verify native restoration and restart |
| Update persistence | `python3 check-update-ownership.py setup`, `verify`, `cleanup` | Active Desktop around an externally run update; new rootfs identity; unchanged home inodes, mixed owners, modes, hardlinks, symlinks and xattrs |
| Host update interruption | `python3 check-update-interruption.py --bundle BUNDLE --sha256 SHA256 --yes` | Desktop inactive; SIGKILL after atomic host launcher replacement; resume with the same bundle/checksum |
| Shared Trash | `unshare --mount --propagation private python3 check-trash.py --installed-policy` | Run a temporary copy inside LXC as mapped guest root; private buses run as `rocknix`; share fixtures are restored or remain recoverable |

`check-init-recovery.py` and `check-preflight-recovery.py` import
`check-component-recovery.py`; keep those files together. Recovery checks close
apps. If startup override cleanup is interrupted, stop Desktop and run
`python3 check-component-recovery.py remove-startup-override` before reopening.
The host-file interruption check retries the ordinary updater with its original
verified bundle. It uses a complete component manifest and exercises rootfs/host rollback before retry. Do not remove an update
journal manually.

Failure injections establish only the named checkpoints. They do not simulate
an arbitrary power cut, a complete-container OOM, or a kernel isolation audit.
Scripted input, screenshots, process checks and audio routing probes do not
establish physical controller/touch ergonomics or audible speaker output. Keep
injected results separate from any later physical-user approval. Never write
fixtures into native account/package/firmware state or delete shared user data.
