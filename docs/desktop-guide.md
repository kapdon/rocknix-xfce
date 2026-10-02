# Desktop controls and window behavior

## Controller and touch

Tap Apps or Settings, then tap a row or navigate with D-pad and the bottom face
button. Printed button labels vary; these mappings use physical positions.

| Control | Action |
| --- | --- |
| D-pad | Arrow keys and launcher selection |
| Bottom face | Enter / confirm |
| Right face or Start | Escape / back |
| Left face (West) | Tab / next field |
| Top face (North) | Shift+Tab / previous field |
| Select | Cycle tabbed and floating apps |
| L3 | Show/hide keyboard |
| R3 | Normal close of the focused app, once per press |
| Right stick | Pointer |
| Left / right trigger | Left / right pointer click |
| Right / left bumper | Scroll up / down |
| Left stick | W/A/S/D |
| Guide / Quick Access | Native InputPlumber UI events |

Tap and release North for individual steps. Holding it also holds Shift, so it
can modify simultaneous clicks or keys. Avoid overlapping North and West:
both use the virtual Tab key. Applications determine their field order; Tab
can insert indentation in editors and terminals. Use D-pad in Apps.
See the [input profile](../payload/input/desktop.yaml) for the complete mapping.

R3 requests an ordinary close only for the focused app in Desktop. Apps own
their save/discard dialogs and can close without warning. Closing the last app
leaves the panel available. Exit Desktop asks for confirmation with Cancel
selected initially, then closes apps and restores native ROCKNIX. Save first.

## Keyboard

Desktop Mode bundles its own wvkbd; it does not replace the native ROCKNIX keyboard.

- Four-row Simple typing layout with staggered letters and larger Shift/Backspace.
- **123** opens one four-row numbers/symbols page; **ABC** returns to typing.
- Shift provides uppercase letters and alternate symbols. Shift+Space sends Tab.
- **Cmp** opens character variants after selecting a letter, such as accented vowels.
- No dedicated navigation page or arrow keys in the normal two-page cycle.
- Roboto, charcoal keys, white labels and gray pressed states match the desktop.

Panel, launcher and keyboard sizing use the active output's logical dimensions;
the RP6 configuration is not a universal sizing preset.
See [keyboard source and build notes](../build-support/wvkbd/README.md).

## Window layout

One tabbed workspace is the default. Select and Windows include both tabbed and
floating apps. Firefox Picture-in-Picture floats at the bottom-right of the usable
workspace. Audio/network utilities float when they fit and become tabbed when
space is limited, including while the keyboard is visible. Normal app windows
remain tabbed; transient dialogs retain Sway's behavior.

PiP matching currently requires the bundled Firefox's English window title.
Unknown titles keep ordinary window behavior. Fullscreen windows keep their
layout. Keyboard visibility changes the usable area, so a utility can switch
between floating and tabbed layouts as space changes. Hide the keyboard if the
standard network editor's Save/Cancel controls are difficult to reach.

## File chooser

Portal-aware LXC applications use the GTK file chooser. The image includes
`xdg-desktop-portal` and `xdg-desktop-portal-gtk`; the Desktop session selects the
ROCKNIX backend configuration and exports its Wayland environment before starting
the private session bus. No host bus connection is needed.

Retained containers keep their installed packages. If upgrading an older
container, install the missing packages from its terminal:

```sh
sudo apt-get update
sudo apt-get install --no-install-recommends xdg-desktop-portal xdg-desktop-portal-gtk
```

After applying the updated Desktop session/configuration, exit Desktop and enter
again so D-Bus activation inherits the correct environment. Installing these
packages does not enable the unimplemented Browse function in the tested native
ARM64 Steam client; see the [RP6 file chooser findings](../experiments/steam-lxc/FILE-CHOOSER.md).

## Display settings

Settings → Display settings previews an advertised resolution/refresh rate or
scale for 15 seconds. Keep saves it; an unconfirmed change reverts automatically.
Desktop defaults to 1.0× and restores the host display on exit. Supported
output choices come from the active device; eligibility is not validation of
every resolution, scaling choice or touch target.

## Native Steam games

Apps → Steam games lists installed titles from ROCKNIX's native Steam libraries.
Settings → Gamescope settings controls what happens when one is launched:

- **Close Desktop** (default) closes desktop apps and stops LXC before starting
  native gamescope. Save your work; the launch menu asks for confirmation.
  Closing Steam/gamescope returns to a fresh Desktop session; closed apps are not
  restored. Quitting only the game leaves Steam open.
- **Keep Desktop running** leaves your apps available beside gamescope. Opening
  Steam games again offers a stop action. Exiting Desktop also stops this game
  session.

The choice persists across Desktop restarts. Both options run native ARM64 Steam
outside LXC using nested Wayland gamescope at 1280×720, with host Sway retained.
This requires the existing native Steam runtime and installed game libraries;
it does not install Steam or provide native Steam's broken Browse dialog.
Close another Steam session before launching here. The launcher owns one game
session, restores native binfmt state after it ends, and stops it if host available
RAM drops below 1.5 GiB. Frame generation is disabled for this initial integration.

RP6 validation currently covers Satisfactory reaching its main menu and the
Desktop lifecycle, not loaded-factory gameplay, controller/audio acceptance or a
full image build. See the [FPS and handoff record](../experiments/steam-lxc/NATIVE-FPS.md).
