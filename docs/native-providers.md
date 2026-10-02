# Experimental native providers

This branch supports an RP6-only host-controlled experiment. Without the
protected `managed/host/state/native-providers` file, Desktop uses its packaged
providers. This selection is not a guest setting or a release default.

The native root account can select `vulkan`, `graphics`, or `codecs` in that
file, owned by root and not writable by other accounts. Stop Desktop before
changing the selection. Remove the file to restore packaged providers on the
next start.

`vulkan` selects native Turnip with its matching libdrm, libdisplay-info, and
Wayland client dependencies. Desktop generates a Vulkan manifest pointing at
the scoped library mounts. The guest retains its Vulkan loader and libc.

`graphics` also selects matching native Mesa EGL, GLX, GBM, Gallium, MSM DRI,
and the GBM DRI backend. The EGL vendor manifest and plugin paths are scoped
to these mounts. Firefox's decoder broker needs the manifest and plugin
directories in its inherited library search paths to create the GL context
used for hardware video frames. Browser sandbox settings remain enabled.

`codecs` additionally imports one native FFmpeg family and dav1d. Only the MPV
and Firefox wrappers select that codec directory. Other programs retain their
packaged codecs. This is a diagnostic mode: native codecs have failed required
Iris playback lifecycle checks and must not replace the packaged corrections.

All imported files are individually mounted read-only with `nosuid,nodev`.
Sources must resolve within the fixed firmware library directories, have
trusted native-root ownership and ancestors, and contain ARM64 ELF headers.
There is no broad `/usr/lib` mount or native libc/loader substitution. The
session resolves selected libraries with the guest loader before opening the
desktop; unresolved dependencies terminate the session. Normal stop/recovery
removes the experiment's mounts and generated manifests.

Files are resolved again on each start, including the single native Gallium
version. A firmware update can therefore supply new providers without copying
them into the rootfs. This does not guarantee ABI or behavior compatibility:
new dependencies, SONAMEs, manifests, driver behavior, or application behavior
still require qualification. Missing or ambiguous sources fail explicitly.

## Qualification boundaries

Native ARM64 rendering and physical-panel captures must be checked on the
exact installed firmware and local bundle. Decoder discovery and successful
library loads do not prove progressing video, working seek, or EOF cleanup.
Keep MPV's four Iris corrections until native implementations pass those
scenarios. A coherent Debian-targeted build of native FFmpeg sources and
patches is a separate source-reuse experiment, not evidence that unmodified
native binaries work.

GLX library loading alone does not qualify Xwayland. Desktop supplies a guest
Xwayland Satellite bridge without importing native X11 sockets or authentication.
Packaged Mesa GLX and optional native-provider GLX require separate rendering
checks. FEX also selects its own runtime library path; native ARM64 provider
results do not qualify x86 translation. Scripted input, captures, and digital audio evidence do not
replace physical-user acceptance of touch, controls, sound, and A/V sync.

Device addresses, credentials, scenario scripts, build logs, and raw acceptance
evidence belong in a private handoff rather than this public document.
