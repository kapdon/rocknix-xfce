#!/usr/bin/env python3
import runpy
from pathlib import Path
api = runpy.run_path('rootfs-overlay/usr/local/bin/rocknix-x11-workarea')
def state(rect, workspace):
    keys = ('x', 'y', 'width', 'height')
    return dict(format=1, output=dict(name='screen', rect=dict(zip(keys, rect))),
                workspace=dict(zip(keys, workspace)))
translate = api['translate']
base = state((0,0,1920,1080), (0,0,1920,1000))
assert translate(base, {'screen':(0,0,1920,1080)}) == (0,0,1920,1000)
assert translate(state((0,0,1920,1080),(0,0,1920,622)),
                 {'screen':(0,0,1920,1080)}) == (0,0,1920,622)
# Negative host origin, RandR offset, scaling, rotation and top reservation.
assert translate(state((-960,0,960,540),(-960,30,960,470)),
                 {'screen':(0,0,1920,1080)}) == (0,60,1920,940)
assert translate(state((0,0,540,960),(0,0,540,900)),
                 {'screen':(1920,0,1080,1920)}) == (1920,0,1080,1800)
for bad in (None, {}, state((0,0,100,100),(0,0,101,100)),
            state((0,0,100,100),(0,0,True,100))):
    try: translate(bad, {'screen':(0,0,100,100)})
    except (ValueError, TypeError, KeyError): pass
    else: raise AssertionError('invalid bounds accepted')
try: translate(base, {})
except KeyError: pass
else: raise AssertionError('missing RandR output accepted')
print('PASS: X11 work-area transforms, reservations and invalidation')
