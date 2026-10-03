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

## Stock ROCKNIX DRM baseline

The user's “without gamescope” clarification meant without **our custom nested
session**, using the stock ROCKNIX launch path. On the same RP6, invoked the actual
EmulationStation command:

```sh
/usr/bin/runemu.sh /storage/.local/share/applications/Satisfactory.desktop \
  -Psteam --core=steam --emulator=steam --controllers=""
```

LXC and EmulationStation were stopped first. A bounded systemd service supervised
the test; `_STEAM_SCOPE=1` prevented the native launcher escaping that service into
its own scope. Added only MangoApp CSV configuration, a five-minute test limit and
an independent available-memory cutoff. Recovery restored prior binfmt and CPU/GPU
governors and started Sway, EmulationStation and Desktop.

The installed `/usr/bin/start_steam_arm64.sh` and `/usr/bin/start_steam.sh` selected
`--backend drm`, stopped host Sway, and ran gamescope with `-W 1080 -H 1920 -r 120`,
`--force-orientation left`, `--xwayland-count 2`, `--mangoapp`, and `-e`. Native Steam
used `-deckard -steamos3 -gamepadui -noshaders` and the game's desktop-file URI.
Both Sway and Desktop were inactive during the measurement. X11 geometry confirmed
the focused Satisfactory window was **1280×720**; the captured output was 1920×1080.
The existing game settings retained fullscreen, VSync off and no frame limit.

A gamescope screenshot verified the full animated main menu (game version
1.2.4.0, CL502094). CSV `mangoapp_2026-10-02_16-50-44.csv`, elapsed **100–155 s**:
**2,072 frames, 37.68 FPS** reciprocal mean frame time, median instantaneous FPS
**38.70**. This is about **7.7% above** the earlier 35.00 FPS nested/LXC-stopped run,
and about **5.0% above** the earlier 35.88 FPS nested/LXC-running run. These are
single menu runs, not a controlled estimate of backend or container overhead.

What the live native source and runtime establish:

- DRM replaces host Sway instead of adding gamescope beneath it. This is a useful
  candidate for the Desktop's close-before-launch mode; the measured improvement
  does not by itself establish composition as its cause.
- The stock launcher briefly requests CPU performance mode during setup, then
  applies the configured game governor. The observed steady governor was
  `ondemand` on all three CPU policies, with GPU `simple_ondemand`, matching the
  earlier Desktop tests. There was no configured core restriction or FPS cap.
- Lossless Scaling frame generation was disabled. Native WSI was active; our
  successful nested handoff explicitly disabled it after an Unreal swapchain
  assertion. Do not transfer that workaround to DRM without testing.
- Stock output targeted 120 Hz while nested targeted 60 Hz. Substantial existing
  swap use and differing temperature/cache state remain confounders. Available
  RAM was roughly 2.1 GiB in the settled menu and swap was almost full.
- Native game audio initialization logged a failure. This FPS run does not qualify
  audio, controller behavior, loaded-save performance or overall launch parity.

No production launcher change follows from this comparison yet. A DRM handoff
would need to stop and restore host Sway as well as LXC, and preserve the native
orientation/input lifecycle. Raw CSV and captures are private under
`/tmp/steam-performance` locally and `/tmp/stock-performance` on RP6.

On stopping the test, native launcher cleanup raced the recovery service's first
Desktop start (the job was canceled). Once Sway and EmulationStation were active,
an explicit Desktop start succeeded. Final check: all three services active, all
three native binfmt handlers enabled, no game/Steam/gamescope process remaining,
CPU governors restored, and a fresh host screen capture succeeded. This cleanup
race is another reason to qualify a production DRM handoff before adopting it.

## Close-mode production integration: stock DRM

At the user's request, Close Desktop now invokes stock `runemu.sh` / Steam DRM
launch instead of our nested launcher. Keep Desktop remains nested. Existing native
Steam shortcuts are reused by matching the selected app ID, preserving ROCKNIX's
filename-based game settings; otherwise a host-owned app-ID shortcut is generated.
Close mode does not inherit the nested WSI or frame-generation overrides.

The close-mode service no longer binds to or orders after Sway, so the native
launcher can stop it without terminating the game or deadlocking recovery.
Recovery restores saved governors and binfmt, starts Sway and EmulationStation,
then waits and retries Desktop startup. It retains its durable session record if
Desktop fails to return. Keep mode retains its Desktop/Sway service bindings.

RP6 acceptance: using the actual Apps menu, selected Steam games → Satisfactory
and confirmed closing apps. Both LXC Desktop and Sway became inactive while stock
DRM gamescope ran at the native orientation/refresh. A fresh screenshot verified
Satisfactory's main menu. Issued gamescope's normal `shutdown` command; Desktop
returned automatically, a fresh capture showed its Apps/Settings panel and Thunar,
and the session record cleared. No Steam/gamescope processes remained; binfmt and
CPU governors were restored. No manual recovery command was needed for this run.
Eight lifecycle/boundary tests passed, along with the full repository source checks.
This narrow live deployment does not add loaded-save or audio/controller acceptance.

## EmulationStation shortcut catalog and overlay follow-up

The Desktop game catalog now reads EmulationStation's Steam shortcut directory,
`/storage/.local/share/applications`, each time it refreshes. It no longer scans
Steam app manifests or generates a fallback shortcut. Entries must contain a name
and an exact Steam `rungameid` URI; arbitrary commands and the Steam client entry
are excluded. Removing a shortcut invalidates later launch requests. Close mode
passes the original filename to stock ROCKNIX, retaining per-game settings. Keep
mode uses its URI but does not yet import ROCKNIX's per-game configuration helpers.

The follow-up overlay test exposed the Unreal swapchain image-count assertion
once in stock DRM, before any overlay keypress. A retry reached the menu but was
stopped by the 1.5 GiB available-memory guard; swap was full after repeated tests.
Neither event establishes an overlay fault. Restarted the dev device before the
next overlay attempt. Earlier FPS tests did not disable Steam overlay, but did not
verify that it could open; MangoApp's FPS display is a separate overlay.

After reboot, stock DRM reached the animated main menu with ample memory.
Shift+Tab and Ctrl+1 from a temporary keyboard produced no visible Steam overlay.
Direct XTest input reached the game (menu interaction changed), but Shift+Tab on
the game's X display and Ctrl+1 on Steam's display still did not expose an overlay.
Gamescope focus inspection did not show an overlay window. This does not qualify
physical Guide-button behavior, and the cause has not been established.

Keep Desktop also reached the main menu using the shortcut's Steam URI. Shift+Tab
on its game X display (and the alternate nested X display) showed no Steam overlay
in a full host capture. Therefore neither mode's overlay is accepted as working.
Stopped the test; Desktop and Sway stayed active, the lease cleared, and no Steam
or gamescope process remained. The saved default remains close. Source checks and
eight catalog/lifecycle tests passed. Physical Guide-button testing and overlay
root-cause diagnosis remain outstanding.

## Controller focus switching and touchscreen override

Keep mode now polls host Sway focus at 0.5-second intervals and checks the focused
process's systemd cgroup against our owned game service. It switches InputPlumber
device 0 between the saved native profile and Desktop's profile. Window names are
not trusted for ownership. The virtual targets are not reset during these changes.
The panel's Pad control offers Automatic, Desktop controls and Game controls;
overrides reset to Automatic at the next session. Errors in the focus watcher stop
the owned game session; durable ExecStopPost restores Desktop controls when Desktop
is still active, while Desktop shutdown retains its native-profile restoration.

Live RP6 check: Satisfactory reached its menu. Game focus selected native
`default.yaml`; Thunar focus selected `desktop.yaml`. Panel pointer activation
applied both manual overrides and then Automatic. Forced SIGKILL of the supervisor
while game controls were active restored Desktop controls, cleared the session and
panel state, and left Desktop/Sway active without Steam/gamescope processes.
The DualSense `/sys/class/input/js1` symlink remained the same `input8/js1` device
throughout focus changes, overrides and recovery. No virtual-controller recreation
was observed. Eleven catalog/controller/lifecycle tests and full source checks passed.
Physical stick/button gameplay and transitions while buttons are held are not yet
accepted; these profile/device observations do not establish Steam overlay behavior.
