# PD2 Launcher: RP6 Wine input and window-size handoff

## Ownership and requested outcome

The PD2 Launcher agent owns its Wine runner, prefix policy and game renderer
integration. RXC owns device exposure and the Sway/Xwayland bridge. Investigate
remaining PD2 touch/rendering behavior without changing the user's D2GL settings
silently, forcing a universal resolution, or changing the host display mode.
No PD2 Launcher source or Wine registry settings were edited by RXC in this pass.

## Tested environment and RXC changes

2026-10-03, Retroid Pocket 6, ROCKNIX 20260930, Debian ARM64 unprivileged LXC,
guest user rocknix UID1000 mapped to host UID201000. Host Sway owns the display;
guest xwayland-satellite 0.8.3 owns Xwayland :0. Wine runs through native FEX
inside LXC. The output is 1920x1080 logical pixels, scale 1. With this tabbed
layout and the bottom panel, Sway assigns the game x=0,y=47,width=1920,height=953.

Installed RXC candidate: `188e9534647b8b94b6bcc000553b79add1b80f6e`.
Component manifest SHA-256:
`94ded96eb2c3182cdc924614d53726ad431f0f60fd6b729abc04a76a5a51c003`.
This is a local validation build with a local package override, not a release.

Two generic RXC defects were addressed:

1. Previously LXC exposed no controller event device. It now binds only the
   qualified native InputPlumber virtual DualSense gamepad and minimal read-only
   udev discovery properties. Current node `/dev/input/event7` is major13/minor71;
   this number is an observation, not a stable API. Physical inputs, hidraw and
   uinput remain absent. The mapped desktop user gets a journaled ACL grant.
2. Satellite accepted an X11 client's resize request beyond Sway's tiled size.
   A plain X11 test reproduced 1920x953 becoming 1920x1080 before the fix.
   The patched bridge now retains the compositor size for tiled/maximized/
   fullscreen clients, with ConfigureNotify feedback; floating resize remains
   allowed. It ships its patched source archive in the xwayland component.

## Controller evidence: no Wine policy workaround required so far

The original `pd2-launcher 0.1.0` package was restored after rootfs replacement,
with identical package SHA and installed file hashes; the existing home/game/
prefix was retained. The game was started with the launcher's visible Play button.
Runner: `lutris-GE-Proton8-26-x86_64`; command: `Game.exe -3dfx -skiptobnet`.
Prefix: `/home/rocknix/.pd2launcher/game/prefix` (the launcher uses retained-FD
paths during execution).

A small read-only 32-bit Windows API probe in that same Wine prefix reports:

| API | Before device exposure | After exposure and real game launch |
| --- | --- | --- |
| XInputGetState(0) | 1167, disconnected | 0, connected |
| XInputGetState(1..3) | 1167 | 1167 |
| joyGetPosEx | no connected index | index 0 succeeds |

`joyGetNumDevs()==16` is capacity, not sixteen connected controllers. Guest UID1000
also successfully opens the virtual event device read/write. Existing winebus
settings already enable SDL and disable hidraw; these settings were not changed.
No additional controller workaround belongs in PD2 Launcher based only on the
old no-device failure. If buttons still fail, first reproduce with Pad: Game and
log XInput state changes in the running prefix, then inspect the game's selected
controller backend/mapping. Enumeration is verified; physical gameplay is not.

## Remaining rendering/touch investigation

After the RXC fix, real Wine reports:

```
GetWindowRect: -3,-22 .. 1923,956
GetClientRect: 0,0 .. 1920,953
ClientToScreen(0,0): 0,0
```

The synthetic X11 test passes all modes: tiled rejects 1920x1080 and stays
1920x953; floating accepts 900x700; fullscreen rejects 800x600 and stays
1920x1080; returning to tiled restores 1920x953.

A later live sample showed the X11 top-level still 1920x953, while its child
`0xa0004e` and Wine's GetClientRect were 1920x1080. Another X11 sample showed the
child back at 1920x953. `_NET_WM_STATE` was empty, override-redirect was false,
and WM_NORMAL_HINTS requested fixed minimum/maximum 1920x1067. These are changing
application-side dimensions; do not assume that every Wine sample agrees with
the top-level, or that the first successful client rectangle settles the issue.

PD2's login artwork still appears vertically cropped. Stored D2GL screen values are window_fullscreen=false,
window_size_width=1920, window_size_height=1080, window_centered=true,
window_position_x/y=0, unlock_cursor=false. These values were read only.
The user's original touch symptom was a fixed shift, not growing edge error.
Post-fix physical touch confirmation remains pending.

Inspect the renderer's actual drawable/viewport and handling of WM_SIZE after
Wine receives the compositor's accepted size. The stored D2GL size and the
current client area differ; this is evidence for further investigation, not
proof of the renderer's exact internal viewport. The launcher source currently
seeds untouched 800x600 D2GL defaults from the physical monitor size in
`src/process/d2gl.rs`. Do not treat physical monitor dimensions as the available
client area for a tiled window. Preserve the user's deliberate render settings.

Satellite presents per-surface X11 coordinates; ClientToScreen origin 0,0 can be
correct while Sway places that surface at y=47. Do not compensate by blindly
adding/subtracting the panel or tab height. Check client-relative pointer
coordinates and the renderer's coordinate transform separately. The output
remaining 1920x1080 is also correct; individual window allocation is 1920x953.

A standalone probe immediately after Desktop restart failed to start FEXServer;
the actual launcher Play path then started the game successfully and subsequent
probes passed. Treat standalone diagnostics without the launch environment
separately from successful production launch; no FEX change was made here.

## Suggested acceptance

- With Pad: Game, show physical button/axis changes in XInput and in PD2.
- Compare mouse and physical touch near center and edges in windowed and
  fullscreen modes, recording Sway allocation, Wine client rect and viewport.
- Resize/toggle modes without altering persistent D2GL preferences; verify
  rendering and hit targets follow the accepted client area.
- Keep launcher modifications in the PD2 repository. If a generic bridge issue
  remains, return a minimal non-game-specific reproduction to RXC.

No login, account creation or gameplay was performed. The game was left open
for the user's physical test. No push, merge, hosted build or release occurred.
