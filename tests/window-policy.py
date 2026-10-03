#!/usr/bin/env python3
"""Run real host policy/cycling logic with fixture Sway IPC responses."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

POLICY = Path('payload/bin/rocknix-window-policy').resolve()
CYCLE = Path('payload/bin/rocknix-window-cycle').resolve()

def window(id, app='firefox-esr', title='Picture-in-Picture', focused=False, **extra):
    return dict(type='con', id=id, app_id=app, name=title, focused=focused,
                shell='xdg_shell', geometry=dict(width=640, height=360),
                nodes=[], floating_nodes=[], **extra)

def workspace(nodes=(), floating=(), width=1920, height=1000, x=0, y=0,
              name='98:Desktop'):
    return dict(type='workspace', name=name, nodes=list(nodes),
                floating_nodes=list(floating),
                rect=dict(x=x, y=y, width=width, height=height))

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    fixture, log = root / 'tree', root / 'commands'
    stub = root / 'swaymsg'
    stub.write_text('''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
if sys.argv[1:] == ['-r', '-t', 'get_tree']:
    print(Path(os.environ['TREE']).read_text())
    sys.exit(int(os.environ.get('QUERY_STATUS', '0')))
with open(os.environ['COMMANDS'], 'a') as f:
    f.write(json.dumps(sys.argv[1:]) + '\\n')
print('[{"success":true}]')
''')
    stub.chmod(0o755)
    env = {**os.environ, 'TREE': str(fixture), 'COMMANDS': str(log),
           'ROCKNIX_RUNTIME_DIR': directory, 'ROCKNIX_BAR_HEIGHT': '80',
           'PATH': directory + ':' + os.environ['PATH']}

    def run(tree, script=None, failure=False):
        fixture.write_text(json.dumps(tree))
        log.unlink(missing_ok=True)
        subprocess.run(['bash', '-c', script or 'source "$1"; policy_tick',
                        'test', str(POLICY)], check=True,
                       env={**env, 'QUERY_STATUS': '1' if failure else '0'}, timeout=5)
        return [json.loads(line)[-1] for line in log.read_text().splitlines()] if log.exists() else []

    # Publish layer-shell usable workspace bounds, independently of client sizes.
    run(dict(type='output', name='DSI-1', rect=dict(x=0,y=0,width=1920,height=1080),
             nodes=[workspace(height=1000)]))
    area = json.loads((root / 'workarea.json').read_text())
    assert area['workspace']['height'] == 1000
    assert area['output']['name'] == 'DSI-1'
    assert area['client'] is None
    tiled = window(15, title='App', focused=True, window_rect=dict(x=0,y=47,width=1920,height=953))
    floating = window(16, window_rect=dict(x=0,y=0,width=640,height=360))
    run(dict(type='output', name='DSI-1', scale=1.25, rect=dict(x=0,y=0,width=1920,height=1080),
             nodes=[workspace([tiled], [floating])]))
    area = json.loads((root / 'workarea.json').read_text())
    assert area['client']['height'] == 953
    assert area['output']['scale'] == 1.25
    assert area['updated_at'] > 0
    run(dict(type='output', name='DSI-1', rect=dict(x=0,y=0,width=1920,height=1080),
             nodes=[workspace(height=622)]))
    assert json.loads((root / 'workarea.json').read_text())['workspace']['height'] == 622
    run(workspace(name='Gaming'))
    assert json.loads((root / 'workarea.json').read_text()) is None

    pip = window(7)
    # Startup must not send a layout command to a surviving floating window
    # when the containing workspace is already tabbed (real RP6 regression).
    startup = Path('payload/bin/launch-sway-desktop').read_text()
    layout_block = startup.split('if ! swaymsg -r -t get_tree', 1)[1].split('\nfi', 1)[0]
    layout_block = 'set -e; DESKTOP_WORKSPACE=98:Desktop; if ! swaymsg -r -t get_tree' + layout_block + '\nfi'
    already_tabbed = workspace(floating=[dict(window(6), type='floating_con', focused=True)])
    already_tabbed['layout'] = 'tabbed'
    assert run(already_tabbed, layout_block) == []
    empty = workspace()
    empty['layout'] = 'splith'
    assert run(empty, layout_block) == ['layout tabbed']
    utility = window(8, 'org.pulseaudio.pavucontrol', 'Volume Control')
    main = window(9, title='Picture-in-Picture — Mozilla Firefox', focused=True)
    commands = run(workspace([pip, utility, main]), 'source "$1"; policy_tick; policy_tick')
    assert len(commands) == 2, commands  # repeated ticks must not fight user moves
    assert 'con_id=7' in commands[0] and 'floating enable, border none' in commands[0]
    assert 'resize set 768 px 432 px' in commands[0], commands[0]
    assert 'move absolute position 1132 px 548 px' in commands[0]
    assert 'con_id=8' in commands[1] and 'floating enable' in commands[1]
    assert (root / 'window-count').read_text().strip() == '3'

    assert 'floating disable' in run(workspace([utility], width=960, height=496))[0]
    assert 'floating disable' in run(workspace([utility], height=622))[0]
    assert run(workspace([main])) == []
    assert run(workspace([window(10, app='unrelated', title='Picture-in-Picture')])) == []
    editor = window(10, app='nm-connection-editor', title='Editing Wi-Fi connection')
    assert 'floating enable' in run(workspace([editor]))[0]
    assert 'floating disable' in run(workspace([editor], height=622))[0]
    assert run(workspace(floating=[dict(window(10, app='nm-connection-editor',
                    title='Discard changes?'), type='floating_con')])) == []
    assert run(workspace([pip], name='Gaming')) == []
    assert run(workspace([dict(pip, id='7; exit')])) == []
    assert run(workspace([dict(pip, fullscreen_mode=1)])) == []
    assert len(run(workspace(floating=[dict(pip, type='floating_con')]))) == 1
    assert run(workspace([pip]), failure=True) == []
    assert run(workspace()) == []
    assert (root / 'window-count').read_text().strip() == '0'

    # Dynamic usable bounds: simulate keyboard showing, then disappearing.
    narrow = root / 'keyboard-tree'
    narrow.write_text(json.dumps(workspace([pip, utility], height=622)))
    wide = root / 'wide-tree'
    wide.write_text(json.dumps(workspace([pip, utility])))
    commands = run(workspace([pip, utility]),
        'source "$1"; policy_tick; cp "$ROCKNIX_RUNTIME_DIR/keyboard-tree" "$TREE"; '
        'policy_tick; cp "$ROCKNIX_RUNTIME_DIR/wide-tree" "$TREE"; policy_tick')
    assert len(commands) == 6, commands
    assert 'floating disable' in commands[3]
    assert 'floating enable' in commands[5]
    assert commands[0] == commands[4]  # original aspect/default restored

    # Tiled+floating traversal must wrap across layers, by stable numeric ID.
    for focused_id, expected in [(7, 8), (8, 9), (9, 7)]:
        tree = workspace([dict(main, focused=focused_id == 9)],
                         [dict(pip, type='floating_con', focused=focused_id == 7),
                          dict(utility, type='floating_con', focused=focused_id == 8)])
        fixture.write_text(json.dumps(tree)); log.unlink(missing_ok=True)
        subprocess.run(['sh', str(CYCLE)], env=env, check=True, timeout=5,
                       stdout=subprocess.DEVNULL)
        assert f'con_id={expected} ' in log.read_text()
    for tree in [workspace(), workspace([main]), workspace([pip, utility]),
                 workspace([main, pip], name='Gaming')]:
        fixture.write_text(json.dumps(tree)); log.unlink(missing_ok=True)
        subprocess.run(['sh', str(CYCLE)], env=env, check=True, timeout=5)
        assert not log.exists()
print('PASS: narrow rules, adaptive bounds, cache, workspace isolation and cross-layer cycling')
