"""GUI checks: implicit descendants, manual reroute reuse, repeat and undo."""
import json
from pathlib import Path
import sys
import traceback
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import smart_align_nodes
from smart_align_nodes.layout_adapter import capture_layout
from smart_align_nodes.layout_route_adapter import generated_nodes, logical_links, socket_index

bpy.context.preferences.view.show_splash = False
area = next(a for a in bpy.context.screen.areas if a.type == 'VIEW_3D')
area.type = 'NODE_EDITOR'; area.ui_type = 'GeometryNodeTree'
tree = bpy.data.node_groups.new('Frame selection regression', 'GeometryNodeTree')
area.spaces.active.pin = True; area.spaces.active.node_tree = tree
smart_align_nodes.register()
state = {'mode': 0, 'phase': 0}
modes = ('frame_only', 'partial_children', 'all_children')
results = []
output = Path('/private/tmp/san_frame_selection_results.json')


def setup(mode):
    tree.nodes.clear()
    f = tree.nodes.new('NodeFrame'); f.name = 'Frame'
    inner = tree.nodes.new('NodeFrame'); inner.name = 'Inner'; inner.parent = f
    a = tree.nodes.new('ShaderNodeMath'); a.name = 'A'; a.parent = inner; a.location = (30, -80)
    b = tree.nodes.new('ShaderNodeMath'); b.name = 'B'; b.parent = inner; b.location = (700, -180)
    r = tree.nodes.new('NodeReroute'); r.name = 'Existing Route'; r.parent = inner
    r.location = (400, -400); r.label = 'Keep label'; r['user_data'] = 7
    tree.links.new(a.outputs[0], r.inputs[0]); tree.links.new(r.outputs[0], b.inputs[0])
    c = tree.nodes.new('ShaderNodeMath'); c.name = 'C'; c.parent = f; c.location = (1100, -180)
    fixed = tree.nodes.new('ShaderNodeMath'); fixed.name = 'Fixed'; fixed.location = (2000, -180)
    tree.links.new(b.outputs[0], c.inputs[0]); tree.links.new(c.outputs[0], fixed.inputs[0])
    for n in tree.nodes:
        n.select = (n.name == 'Frame' or (mode == 'partial_children' and n.name == 'A')
                    or (mode == 'all_children' and n.name != 'Fixed'))


def current():
    return area.spaces.active.node_tree


def positions():
    return {n.name: tuple(n.location_absolute) for n in current().nodes}


def signature():
    t = current()
    return sorted((a.node.name, socket_index(a), b.node.name, socket_index(b), order)
                  for a, b, order, _ in logical_links(t, generated_nodes(t)))


def assert_close(a, b):
    assert a.keys() == b.keys()
    assert max(abs(a[k][i]-b[k][i]) for k in a for i in (0, 1)) < .15, (a, b)


def tick():
    global tree
    try:
        with bpy.context.temp_override(window=bpy.context.window, area=area,
                                      region=next(r for r in area.regions if r.type == 'WINDOW')):
            phase = state['phase']
            if phase == 0:
                setup(modes[state['mode']]); state['phase'] = 1; return .5
            if phase == 1:
                snap, _, meta = capture_layout(tree)
                assert {n.key for n in snap if n.selected} == {'Frame', 'Inner', 'A', 'B', 'C'}
                assert meta['reusable_reroutes'] == ['Existing Route']
                state['before'] = positions(); state['selection'] = {n.name: n.select for n in tree.nodes}
                state['signature'] = signature()
                bpy.ops.ed.undo_push(message='Before Frame selection test')
                assert bpy.ops.smart_align_nodes.auto_layout('INVOKE_DEFAULT') == {'RUNNING_MODAL'}
                state['phase'] = 2; return .6
            if phase == 2:
                report = json.loads(bpy.data.texts['Smart Align Layout Debug'].as_string())
                assert report['metadata']['verified_after_redraw']
                assert report['metrics']['reused_reroutes'] >= 1, report['metrics']
                assert positions()['Fixed'] == state['before']['Fixed']
                assert current().nodes['Existing Route'].label == 'Keep label'
                assert current().nodes['Existing Route']['user_data'] == 7
                assert {n.name: n.select for n in current().nodes if n.name in state['selection']} == state['selection']
                assert signature() == state['signature']
                state['after'] = positions()
                if state['mode'] == 0: state['expected'] = positions()
                else: assert_close(positions(), state['expected'])
                bpy.ops.smart_align_nodes.auto_layout('INVOKE_DEFAULT')
                state['phase'] = 3; return .6
            if phase == 3:
                assert_close(positions(), state['after'])
                bpy.ops.ed.undo(); bpy.ops.ed.undo()
                state['phase'] = 4; return .3
            if phase == 4:
                assert_close(positions(), state['before'])
                assert {n.name: n.select for n in current().nodes} == state['selection']
                assert signature() == state['signature']
                bpy.ops.ed.redo(); state['phase'] = 5; return .3
            if phase == 5:
                assert_close(positions(), state['after']); assert signature() == state['signature']
                results.append({'mode': modes[state['mode']], 'pass': True, 'reuse_repeat_undo_redo': True})
                state['mode'] += 1
                tree = current()
                if state['mode'] < len(modes): state['phase'] = 0; return .1
                output.write_text(json.dumps(results, indent=2))
                print('SAN_FRAME_SELECTION_PASS', flush=True); bpy.ops.wm.quit_blender(); return None
    except Exception:
        results.append({'failure': traceback.format_exc()}); output.write_text(json.dumps(results, indent=2))
        traceback.print_exc(); bpy.ops.wm.quit_blender(); return None
    return .2


bpy.app.timers.register(tick, first_interval=1.5)
