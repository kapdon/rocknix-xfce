# PD2 windowed-mode size: handoff to LXC

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
