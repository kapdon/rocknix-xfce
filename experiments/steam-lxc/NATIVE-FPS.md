# Native nested gamescope FPS check — 2026-10-02

Satisfactory launched through native Steam `-applaunch 526870`, while the ordinary
LXC Desktop remained active. This is a menu measurement, **not gameplay FPS**.

- Existing native-gamescope/session.sh, with temporary `--mangoapp`, a 300-second
  unit limit and independent 1.5 GiB MemAvailable cutoff. No SDL override.
- Gamescope input/output 1280x720, refresh target 60 Hz; frame generation disabled.
- Existing game configuration: 1280x720, VSync off, mostly quality level 0, with
  reflection/shading/landscape entries at 3. Settings were not normalized to a preset.
- MangoApp CSV: 1,974 frame samples in elapsed seconds 70–125, after the main menu
  appeared. Reciprocal mean frame time: **35.88 FPS**; median instantaneous FPS:
  **37.67**. Captured overlay readings: 35, 37 and 38 FPS in the animated menu.
- No save was successfully loaded. Pointer interaction did not activate Load;
  subsequent X11 input and screen capture stalled. Cause is not established.
- Host available RAM fell to about 1.9 GiB; swap use reached about 5.3 GiB.
  Kernel journal reported memory pressure. This does not prove pressure caused
  the graphics stall. No native fullscreen baseline was measured.
- Stopped the test. Steam/gamescope processes were absent; all three native binfmt
  handlers were enabled; Desktop remained active and a fresh capture succeeded.
  Available RAM recovered to 6.3 GiB.

Private raw CSV and captures are retained locally under /tmp/native-steam-poc.
Do not interpret the configured 60 Hz refresh as measured FPS or this menu result
as an estimate for a loaded factory. Gameplay and nested-versus-native overhead
remain unmeasured.

## Desktop-menu launch with LXC stopped

The user requested a second baseline initiated from the LXC desktop itself.
Installed a temporary **Satisfactory baseline** Apps entry. A fixed FIFO request
was accepted while Desktop was active, then an independent host service stopped
LXC and EmulationStation before starting native Steam/gamescope. Host Sway stayed
running; this was **not** standalone DRM gamescope.

The first run crashed before a usable main menu. The game log asserted:
`CreateSwapchain, image count is not expected to change` in VulkanViewport.cpp:795.
A retry with `ENABLE_GAMESCOPE_WSI=0` reached the animated main menu. This is an
observed successful compatibility variant, not proof of the crash's root cause.
[Upstream WSI layer source](https://github.com/ValveSoftware/gamescope/blob/master/layer/VkLayer_FROG_gamescope_wsi.cpp)
is the reference for gamescope's Vulkan layer; the setting does not change the
Wayland compositor backend.

| Run | LXC | MangoApp sampling window | Frames | Reciprocal mean frame time |
| --- | --- | --- | --- | --- |
| Earlier nested test | running | elapsed 70–125 s | 1,974 | 35.88 FPS |
| Desktop-menu handoff, WSI disabled | stopped | elapsed 100–155 s | 1,926 | 35.00 FPS |

Second-run median instantaneous FPS was 38.12. Both used 1280×720 and the existing
mixed low graphics configuration above, without frame generation. The successful
second-run CSV is `mangoapp_2026-10-02_16-22-50.csv`. It contains loading samples
outside the selected main-menu window; those are excluded from this comparison.
The crash reporter's FPS in the failed first run is not used.

No clear menu FPS improvement was demonstrated. Different WSI configuration,
thermal/cache state and substantial pre-existing swap use prevent treating this
as a controlled measurement of LXC overhead. Gameplay remains unmeasured.

## Integrated setting and device acceptance

Implemented **Settings → Gamescope settings** with persisted `close`/`keep`
choices, and **Apps → Steam games → Satisfactory**. Guest requests carry only a
validated installed app ID and mode over the existing host-control FIFO. Native
Steam launches in an independent systemd unit with cgroup cleanup and a durable
binfmt restoration record. Close mode confirms closing apps first. A host-memory
watchdog stops the session below 1.5 GiB available; no five-minute production limit
or benchmark overlay is installed.

On the existing `222bbb4` RP6 installation, narrow patches preserved newer installed
code. The new integrated path was physically observed reaching Satisfactory's main
menu in **both** modes. Close mode showed LXC inactive; keep mode showed both units
active and retained the Desktop panel/Thunar. The keep preference survived a full
Desktop restart. The keep-mode Apps menu's **Stop game and Steam** action stopped
the game unit and preserved Desktop. Stopping the close-mode game unit restored a
fresh Desktop session. All x86/box32/box64 binfmt handlers were enabled afterward,
with no Steam/gamescope processes remaining.

The temporary experiment initially attempted to restart Desktop with EmulationStation
still stopped, which its preflight correctly rejected. The integrated recovery now
starts EmulationStation before Desktop; this return path passed on the device.
The temporary Apps entry was removed. Final device state: Desktop active, setting
`close`, no test game session active. The native Steam backup remains untouched.

Full repository source checks passed, including seven new games lifecycle/boundary
tests. This is a source plus narrow live-deployment validation, not a full image
build, publication, loaded-save test, controller/audio acceptance or native DRM
comparison. Native Gaming Mode's launcher does not yet participate in the same
lock; this launcher refuses an already-running native Steam session, but an
external simultaneous launch race is not qualified.
