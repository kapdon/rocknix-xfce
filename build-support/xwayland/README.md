# Xwayland compositor geometry

`compositor-size.patch` applies to the pinned xwayland-satellite 0.8.3 source.
It keeps compositor-assigned dimensions for tiled, maximized and fullscreen
windows when an X11 client submits a later ConfigureRequest. A synthetic
ConfigureNotify reports the accepted geometry even when the real size does not
change. Floating windows retain client-driven resizing.
The patch also reconciles X11 fullscreen state on every compositor configure,
including a stale client flag when the cached Wayland state did not change.

The regression fixture checks transitions between constrained and floating
states. Its test compositor encodes states as native-endian 32-bit values, as
required by the Wayland protocol, instead of one byte per state.

The component ships its patched source and original upstream license. Device
validation must compare Sway, X11 and application geometry; compilation alone
does not establish correct rendering or touchscreen coordinates.
