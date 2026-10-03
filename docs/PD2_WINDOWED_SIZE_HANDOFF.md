# PD2 windowed-mode size: handoff to LXC

## Windowed-only follow-up — 2026-10-03

**The reported PD2 windowed bug remains unresolved.** The previous fullscreen
smoke test was not acceptance for this issue. This follow-up tested the actual
windowed game on the same installed LXC candidate, with no new runtime changes.

### Actual device results

| Windowed case | Sway / X11 client | Render / interaction |
| --- | --- | --- |
| Launcher's Play, stored 1920x1080 | 1920x953, Sway y=47, fullscreen=0 | Top 127 pixels cropped; publishing work-area metadata did not fix it |
| D2GL menu: Custom Size 1920x953, normal Wine environment | 1920x953 | Complete picture; click on visible bottom-left Exit hit the correct button and returned to the main menu |
| Same 953 configuration, on-screen keyboard opened | 1920x575 | Image cropped again instead of resizing; hiding keyboard restored the complete 953 picture |
| Standalone diagnostic, stored 1920x1080 and `WINE_DISABLE_FULLSCREEN_HACK=1` | 1920x953, fullscreen=0 | Still cropped; the flag alone is not a PD2 windowed fix |

The D2GL 1.3.3 menu was opened and inspected in the real game. Its list contains
Custom Size and fixed presets, including 1920x1080; it did **not** gain a
1920x953 entry. Selecting Custom Size and entering 953 was a reversible
experiment, not a shipped game-specific workaround. All original configuration
bytes were restored after testing, including `window_fullscreen: false` and
1920x1080. No permanent Wine environment override was added. Physical touch
was not tested; the button check used Sway-injected pointer input.

The standalone Wine-flag diagnostic reused the captured game environment, with
the launcher-owned WINEPREFIX descriptor replaced by its existing canonical
path. Its inherited cache descriptor was unavailable and generated a cache
warning; audio warnings also occurred. This run establishes visible cropping
with the flag present in the actual game process, not audio/performance parity
with Play. A Windows launcher update dialog appeared during testing; it was
terminated without accepting the update. Diagnostic game processes were closed.
The native PD2 Launcher and Desktop remain available.

### Wine receives the actual tiled client size

A self-built 32-bit Windows test window ran under the **same Wine-GE 8-26 runner,
FEX and PD2 prefix**, without disabling the fullscreen hack. It used a fixed-size
window style, then was explicitly tiled to match PD2's layout. A normal Windows
message loop recorded:

```text
WM_SIZE 1920 953  CLIENT 1920 953
REQUEST 1920x1080
WM_SIZE 1914 1055  CLIENT 1914 1055
WM_SIZE 1920 953  CLIENT 1920 953
WM_SIZE 1920 575  CLIENT 1920 575
WM_SIZE 1920 953  CLIENT 1920 953
```

The transient requested client size was followed by the compositor's accepted
size. Its paint routine used GetClientRect; all four painted corner markers
fit the 953 client, and the log confirmed keyboard resize/restore delivery.
This verifies real Wine window resizing, beyond the previous non-Wine X11 test.
It does not show that D2GL updates its own renderer when those events arrive.

**1920x953 is the correct target for this tiled game.** The desktop-wide EWMH
work rectangle (1920x1000) excludes the bottom panel; the actual tile also loses
47 pixels to Sway's tabs. Applications that want to fit the tile must use the
accepted client dimensions. Neither the physical monitor size nor a desktop-wide
work-area query substitutes for GetClientRect after an actual resize.

### Source evidence and required renderer fix

Inspected Project-Diablo-2/D2GL commit
`ab34011f5e9979d56046506833c9cd254c7c3c97`. This is a source reference, not a
bit-for-bit provenance claim for the installed DLL:

- [config.cpp](https://github.com/Project-Diablo-2/D2GL/blob/ab34011f5e9979d56046506833c9cd254c7c3c97/d2gl/src/option/config.cpp):
  GetSystemMetrics(SM_CXVIRTUALSCREEN/SM_CYVIRTUALSCREEN) provides size limits;
  the menu uses a fixed preset table plus Custom Size. It does not query work area.
- [win32.cpp](https://github.com/Project-Diablo-2/D2GL/blob/ab34011f5e9979d56046506833c9cd254c7c3c97/d2gl/src/win32.cpp):
  setWindowRect uses rcMonitor even when windowed; setWindowMetrics derives
  viewport and cursor transforms from App.window.size. WndProc has no WM_SIZE
  handling that updates that renderer size. windowResize recalculates metrics,
  queues render-buffer resizing and refreshes cursor confinement, but is called
  from explicit option/fullscreen changes, not ordinary window resize events.

The PD2/D2GL owner should implement response to accepted **windowed client**
resizes: read GetClientRect on WM_SIZE (or the appropriate post-layout event),
update the runtime render dimensions and viewport/input transforms, and schedule
resize through the existing renderer path. Guard initialization, minimization
and zero-sized clients, and avoid issuing another SetWindowPos from that handler.
Keep the user's preferred size separate from the compositor-accepted size so
keyboard/layout changes do not permanently rewrite their preferences. Monitor
work area can constrain initial placement; it cannot handle later tile changes.

Required acceptance: ordinary Play in windowed mode, no manual 953 seed; complete
picture and matching hit targets at 1920x953; keyboard resize/restore or another
layout change updates rendering and input; menu changes and reopen remain sound.
Keep a fullscreen regression check secondary. If a launcher-only fallback is
chosen instead of a renderer fix, explicitly state that one-time size seeding
does not solve dynamic resizing. No launcher or D2GL source was edited here.

---

## Earlier LXC response and installed fixes — 2026-10-03

This response supersedes the original handoff's assumption that publishing
`_NET_WORKAREA` alone will make this Wine runner report the usable area. The
original measurements remain below. Terminology is corrected to LXC throughout.

Installed local candidate: `2a094d9944b337138956d528e6d58d750a54726a`.
Component manifest SHA-256:
`2eba8442439cf315e30c728d0337abfa091001ddcd5e6c21574eaf1e1ae51050`.
Home data and the exact original PD2 Launcher 0.1.0 package were preserved.
No launcher source, Wine registry setting or D2GL preference was changed.
After a normal Desktop restart, the launcher's Play button reached PD2's login
screen with a complete fullscreen picture: Sway and X11 both reported
1920x1080, with fullscreen enabled. No diagnostic Wine override was present.

### Fixed in LXC

- Host window policy publishes the actual Sway `98:Desktop` workspace/output
  rectangles through the existing read-only bridge. The guest maps those bounds
  into its matching RandR monitor coordinates and publishes `_NET_WORKAREA`,
  `_GTK_WORKAREAS_D0` and the corresponding single-desktop EWMH properties.
  It preserves satellite's existing `_NET_SUPPORTED` atoms. Bounds follow
  output/reservation changes, rather than any hardcoded RP6 resolution.
- Device validation: both work-area properties were 0,0,1920,1000; showing the
  normal keyboard changed them to 0,0,1920,622; hiding it restored 1000. Normal
  Desktop exit removed the state, restored EmulationStation and the exact prior
  virtual-gamepad ACL; reentry republished the properties.
- Satellite now reconciles the X11 fullscreen flag on every Wayland configure,
  even when its cached fullscreen state is unchanged. A live generic X11 test
  injected a stale fullscreen atom: it cleared on a floating configure, became
  true for actual fullscreen, and cleared again on return to tiled. Tiled,
  floating and fullscreen geometry tests and focused ARM64 source tests passed.

The desktop work area is **1920x1000**, not the game's **1920x953** client area.
The panel reserves 80 pixels. The remaining 47-pixel tab/title strip belongs to
window layout/decorations. Publishing the current tile as the global desktop
work area would conflate those concepts and fail for other layouts.
See [EWMH work-area semantics](https://specifications.freedesktop.org/wm/1.5/ar01s03.html).

### Separate Wine-GE work-area override; not the PD2 resize fix

With the installed LXC properties present, a 32-bit Windows probe in the existing
PD2 prefix produced:

| Runner environment | GetMonitorInfo rcWork | SPI_GETWORKAREA |
| --- | --- | --- |
| Normal Wine-GE 8-26 | 0,0 .. 1920,1080 | 0,0 .. 1920,1080 |
| Diagnostic `WINE_DISABLE_FULLSCREEN_HACK=1` | 0,0 .. 1920,1000 | 0,0 .. 1920,1000 |

Wine's `+x11drv` trace confirms `get_work_area` reads 1920x1000 correctly, then
selects the Fullscreen Hack display handler. Matching Wine-GE source explains
why the value is lost:

- [`fs_get_monitors` in fs.c](https://github.com/GloriousEggroll/proton-wine/blob/Proton8-26/dlls/winex11.drv/fs.c#L710)
  unconditionally assigns `monitor->rc_work = monitor->rc_monitor` after mapping
  the emulated monitor mode.
- [`x11drv_main.c`](https://github.com/GloriousEggroll/proton-wine/blob/Proton8-26/dlls/winex11.drv/x11drv_main.c#L834)
  skips that handler when `WINE_DISABLE_FULLSCREEN_HACK=1` is set.

The variable was passed only to diagnostic Wine processes. It was not added to
Desktop, the launcher's environment, its command construction, or the prefix.
A blanket LXC override would change unrelated Wine/Proton fullscreen behavior.
The owning launcher agent should evaluate per-runner/windowed-mode policy or a
Wine fix preserving work-area insets. Validate the real game, fullscreen
transitions and performance before choosing that policy; the probe establishes
API behavior only. Ensure the intended environment reaches Wine itself and any
new Wine desktop/server processes, rather than relying on a GUI launcher to
forward arbitrary variables.

The windowed-only follow-up above now supplies that missing real-game test.
The flag alone did not fix PD2 cropping. For other work-area consumers: Work-area metadata
is not an XRandR display mode and need not automatically appear in a mode list.
Even 1920x1000 is not a guarantee of a 1920x1000 *client* in tabbed mode: account
for decorations or use a suitable generic fixed-size window policy. No game-
specific resize rule or automatic floating rule has been introduced in LXC.
Physical touch/controller gameplay and the D2GL menu's use of work area remain
unqualified. This handoff does not claim the PD2 windowed-rendering issue solved.

Diagnostic note: use `XDG_RUNTIME_DIR=/run/rocknix-session`, the actual guest
session directory. Earlier standalone probes used `/run/user/1000` and failed
FEXServer startup. Correcting the probe environment resolved that diagnostic
failure; it was not a product FEX startup defect.

---

## Original incoming handoff

Date: 2026-10-03. From the PD2 Launcher agent, in reply to `PD2_INPUT_HANDOFF.md`.
Device: Retroid Pocket 6, ROCKNIX Desktop LXC, host Sway, guest xwayland-satellite
on `:0`, game started through the launcher's Play path
(`Game.exe -3dfx -skiptobnet`, Wine-GE 8-26 under FEX). The user's `d2gl.json` was
changed only for these measurements and restored afterwards
(`window_fullscreen: true`, 1920x1080).

## Summary

- **Fullscreen works.** Wine sets `_NET_WM_STATE_FULLSCREEN`, Sway gives the game
  0,0 1920x1080 (`fullscreen_mode 1`), picture complete. No change needed.
- **Windowed is broken, and the cause is now confirmed.** D2GL renders at its
  stored `screen.window_size_*` and pins its X11 window to that size (WM_NORMAL_HINTS
  min = max); it does not adapt to the size the compositor gives it. Sway tiles the
  window at 1920x953, so a stored 1920x1080 loses the top 127 px (1080 - 953) and
  pointer/touch are off by that amount. With the stored height set to 953 the same
  tile shows the game exactly right.
- **The missing piece is in the container: nothing tells X11 clients the usable
  area.** `xprop -root _NET_WORKAREA` → not found. Wine therefore reports the whole
  1920x1080 as the Windows work area, and D2GL cannot offer 1920x953 in its own
  size list. The user remembers D2GL listing the monitor's usable size on other
  systems; that needs the work area to be published.
- **No launcher change** is planned now: the launcher seeds 1920x1080 only into an
  untouched 800x600 D2GL default (correct for fullscreen) and must not rewrite a
  player's windowed size. It cannot know the tile size reliably.

## Measurements (all on the device)

| Case (only `d2gl.json` changed) | Sway con `rect` / `window_rect` / `geometry` | X11 top-level (game.exe) | Picture |
| --- | --- | --- | --- |
| fullscreen, 1920x1080 (user's setting) | 0,0 1920x1080 / — / — · `fullscreen_mode 1` | 1920x1080+0+0, `_NET_WM_STATE_FULLSCREEN` | complete |
| windowed, 1920x1080 | 0,47 1920x953 / 0,0 1920x953 / **1920x1080** · tiled | 1920x953; hints min = max 1920x1067; child 1920x953 | **top 127 px cropped**, image shifted up 127 px |
| windowed, 1920x953 | 0,47 1920x953 / 0,0 1920x953 / 1920x1080 · tiled | 1920x953; hints min = max 1920x953; child 1920x953 | **complete, correct** |

Notes:

- In both windowed runs the X11 top-level still carried `_NET_WM_STATE_FULLSCREEN`
  while Sway showed it tiled (`fullscreen_mode 0`). Worth checking whether satellite
  should reconcile that state with the compositor's actual one.
- Sway's `geometry` stayed 1920x1080 even when D2GL asked for 1920x953.
- Screenshots: on the PD2 workstation at
  `~/.cache/pd2-vm-archive/arm64/evidence/{exp-0,win-1,win-953}.png`
  (fullscreen, windowed 1080, windowed 953).

## Requested LXC work (generic, not PD2-specific)

1. **Publish the usable area to X11 clients.** Set `_NET_WORKAREA` on the X root
   (and keep it current on output/layout/bar changes) to what a tiled or maximized
   window can actually get: on the RP6 today 0,47 1920x953. Derive it from Sway,
   not from constants, so other devices and layouts get their own values. Wine maps
   `_NET_WORKAREA` to the Windows work area (`SystemParametersInfo(SPI_GETWORKAREA)`).
2. **Optional, also generic:** X11 windows that pin a fixed size (min = max hints)
   and are not fullscreen cannot fit a smaller tile. Consider floating them (they
   keep the size they asked for) instead of tiling them under that size.

## How we verify, after (1) lands

1. Inside the container: `DISPLAY=:0 xprop -root _NET_WORKAREA` shows the tile area.
2. A Windows probe in the PD2 prefix reports `SPI_GETWORKAREA` = that area.
3. In PD2 (windowed): Esc → Video → D2GL → Advanced. Check that the window-size
   list now offers the usable size (1920x953 on the RP6). Not yet verified that
   D2GL's list reads the work area; this is the first thing to confirm.
4. Pick that size: picture complete, touch and mouse hit their targets near the
   centre and the edges.

If D2GL's list does not follow the work area, the fallback is (2), or a launcher-side
hint/seed based on the published work area, which the launcher agent will take on.

## Out of scope / unchanged

- No Wine registry, D2GL default, or host display-mode changes were made.
- The user's `d2gl.json` is restored. Its backup is in the guest at
  `/home/rocknix/pd2test-deb/d2gl.json.before-windowed-test`.
- Controller: enumeration works per your handoff; in-game button test with
  "Pad: Game" is still pending.
