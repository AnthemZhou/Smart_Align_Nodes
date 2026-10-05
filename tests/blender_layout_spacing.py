"""GUI regression: actual add-on preferences reach Command+O layout columns."""
import json
from pathlib import Path
import sys
import traceback
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import smart_align_nodes
from smart_align_nodes.layout_adapter import capture_layout

bpy.context.preferences.view.show_splash = False
area = next(a for a in bpy.context.screen.areas if a.type == 'VIEW_3D')
area.type = 'NODE_EDITOR'
area.ui_type = 'ShaderNodeTree'
material = bpy.data.materials.new('Spacing regression')
material.use_nodes = True
bpy.context.active_object.data.materials.clear()
bpy.context.active_object.data.materials.append(material)
tree = material.node_tree
tree.nodes.clear()
for name, x in (('A', 0), ('B', 600), ('C', 1200)):
    n = tree.nodes.new('ShaderNodeMath')
    n.name = name
    n.location = (x, 0)
    n.select = True
tree.links.new(tree.nodes['A'].outputs[0], tree.nodes['B'].inputs[0])
tree.links.new(tree.nodes['B'].outputs[0], tree.nodes['C'].inputs[0])
smart_align_nodes.register()
addon = bpy.context.preferences.addons.new()
addon.module = 'smart_align_nodes'
prefs = addon.preferences
assert prefs.layout_horizontal_gap == 100
results = []
state = {'phase': 0, 'index': 0}
gaps = (60, 160, 24)
output = Path('/private/tmp/san_layout_spacing_results.json')


def positions():
    return {n.name: tuple(n.location_absolute) for n in tree.nodes}


def tick():
    try:
        with bpy.context.temp_override(window=bpy.context.window, area=area,
                                      region=next(r for r in area.regions if r.type == 'WINDOW')):
            phase = state['phase']
            if phase == 0:
                before = positions()
                prefs.layout_horizontal_gap = gaps[state['index']]
                assert positions() == before, 'Preference must not mutate an open layout'
                bpy.ops.ed.undo_push(message='Before spacing test')
                assert bpy.ops.smart_align_nodes.auto_layout('INVOKE_DEFAULT') == {'RUNNING_MODAL'}
                state['phase'] = 1
                return .5
            if phase == 1:
                report = json.loads(bpy.data.texts['Smart Align Layout Debug'].as_string())
                assert report['metadata']['horizontal_gap'] == gaps[state['index']]
                snap, _, _ = capture_layout(tree)
                boxes = {n.key: n.box for n in snap}
                measured = [boxes[b].left-boxes[a].right for a, b in (('A', 'B'), ('B', 'C'))]
                assert all(abs(v-gaps[state['index']]) < .15 for v in measured), measured
                state['positions'] = positions()
                state['measured'] = measured
                bpy.ops.smart_align_nodes.auto_layout('INVOKE_DEFAULT')
                state['phase'] = 2
                return .5
            if phase == 2:
                assert positions() == state['positions'], 'Repeat drift'
                results.append({'gap': gaps[state['index']], 'measured': state['measured'],
                                'repeat_stable': True})
                state['index'] += 1
                if state['index'] < len(gaps):
                    state['phase'] = 0
                    return .1
                bpy.context.preferences.view.language = 'zh_HANS'
                bpy.context.preferences.view.use_translate_interface = True
                assert bpy.app.translations.pgettext_iface('Layout Horizontal Gap') == '自动布局横向间距'
                results.append({'chinese_label': True, 'default': 100})
                output.write_text(json.dumps(results, ensure_ascii=False, indent=2))
                print('SAN_LAYOUT_SPACING_PASS', flush=True)
                bpy.ops.wm.quit_blender()
                return None
    except Exception:
        results.append({'failure': traceback.format_exc()})
        output.write_text(json.dumps(results, ensure_ascii=False, indent=2))
        traceback.print_exc()
        bpy.ops.wm.quit_blender()
        return None
    return .1


bpy.app.timers.register(tick, first_interval=1.5)
