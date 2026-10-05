"""Run in an isolated GUI Blender: --factory-startup --python this_file.
Does not save preferences, install addons, or alter any user .blend file.
"""
import json
import os
from pathlib import Path
import sys
import traceback
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import smart_align_nodes
from smart_align_nodes.layout_adapter import capture_layout, capture_restore_state, apply_locations, restore_state
from smart_align_nodes.layout import solve_layout

bpy.context.preferences.view.show_splash = False
PARTIAL = os.environ.get('SAN_PARTIAL_CASE') == '1'
RESULT = Path('/private/tmp/smart_align_layout_partial_results.json' if PARTIAL else
              '/private/tmp/smart_align_layout_blender_results.json')
results = []
state = {'step': 0}
area = next(a for a in bpy.context.screen.areas if a.type == 'VIEW_3D')
area.type = 'NODE_EDITOR'
area.ui_type = 'ShaderNodeTree'
mat = bpy.data.materials.new('SAN Layout Test')
mat.use_nodes = True
bpy.context.active_object.data.materials.clear()
bpy.context.active_object.data.materials.append(mat)
tree = mat.node_tree
tree.nodes.clear()
frame = tree.nodes.new('NodeFrame')
frame.name = 'Frame'
a = tree.nodes.new('ShaderNodeValue'); a.name = 'A'; a.parent = frame; a.location = (30,-80)
b = tree.nodes.new('ShaderNodeMath'); b.name = 'B'; b.parent = frame; b.location = (40,-400)
c = tree.nodes.new('ShaderNodeMath'); c.name = 'C'; c.location = (500,-100)
r = tree.nodes.new('NodeReroute'); r.name = 'R'; r.location = (400,-300)
fixed = tree.nodes.new('ShaderNodeMath' if PARTIAL else 'ShaderNodeValue'); fixed.name = 'Fixed'; fixed.location = (1500,0); fixed.select=False
for n in (a,b,c,r,frame): n.select=True
tree.links.new(a.outputs[0],b.inputs[0])
tree.links.new(b.outputs[0],r.inputs[0])
tree.links.new(r.outputs[0],c.inputs[0])
if PARTIAL:
    frame.select = False
    a.location = (30, -80)
    b.location = (350, -250)
    b.hide = True
    r.location = (850, -280)
    c.location = (1100, -150)
    fixed.location = (1550, -50)
    tree.links.new(c.outputs[0], fixed.inputs[0])
smart_align_nodes.register()


def context():
    return bpy.context.temp_override(window=bpy.context.window, area=area,
                                     region=next(r for r in area.regions if r.type=='WINDOW'))


def positions():
    return {n.name: tuple(n.location_absolute) for n in bpy.data.materials['SAN Layout Test'].node_tree.nodes}


def check_positions(expected):
    current=positions()
    assert all(abs(current[k][i]-v[i])<0.15 for k,v in expected.items() for i in (0,1)), (current, expected)


def signature():
    t=bpy.data.materials['SAN Layout Test'].node_tree
    return [(l.from_node.name,l.from_socket.identifier,l.to_node.name,l.to_socket.identifier,l.multi_input_sort_id) for l in t.links]


def tick():
    try:
        step=state['step']
        with context():
            if step==0:
                snap,links,meta=capture_layout(tree)
                state['before']=positions(); state['links']=signature()
                state['restore']=capture_restore_state(tree)
                bpy.ops.ed.undo_push(message='SAN Before Layout')
                status=bpy.ops.smart_align_nodes.auto_layout('INVOKE_DEFAULT')
                assert status=={'RUNNING_MODAL'}, status
                state['step']=1
                return 1.0
            if step==1:
                report=bpy.data.texts.get('Smart Align Layout Debug')
                assert report is not None, 'Layout did not finish: no debug report'
                report=json.loads(report.as_string())
                assert report['metadata']['verified_after_redraw']
                if PARTIAL:
                    assert report['metrics']['partial_scopes'] == 1
                    assert report['metrics']['node_overlaps'] == 0
                assert positions()!=state['before'], 'No layout movement'
                assert signature()==state['links']
                assert positions()['Fixed']==state['before']['Fixed']
                state['after']=positions()
                bpy.ops.node.view_all()
                bpy.ops.screen.screenshot(filepath='/private/tmp/smart_align_layout_preview.png')
                results.append({'test':'interactive_frame_reroute_layout','pass':True,'report':report})
                bpy.ops.ed.undo()
                state['step']=2
                return 0.4
            if step==2:
                check_positions(state['before'])
                assert signature()==state['links']
                results.append({'test':'one_undo_restores_original','pass':True})
                bpy.ops.ed.redo()
                state['step']=3
                return 0.4
            if step==3:
                check_positions(state['after'])
                results.append({'test':'redo_restores_layout','pass':True})
                bpy.ops.smart_align_nodes.auto_layout('INVOKE_DEFAULT')
                state['step']=4
                return 0.7
            if step==4:
                check_positions(state['after'])
                results.append({'test':'repeat_stability','pass':True})
                t=bpy.data.materials['SAN Layout Test'].node_tree
                restore_state(t,state['restore'])
                state['step']=5
                return 0.4
            if step==5:
                check_positions(state['before'])
                results.append({'test':'restore_after_frame_redraw','pass':True})
                smart_align_nodes.unregister()
                smart_align_nodes.register()
                smart_align_nodes.unregister()
                results.append({'test':'register_reload_unregister','pass':True})
                RESULT.write_text(json.dumps(results,ensure_ascii=False,indent=2))
                print('SAN_GUI_PASS',flush=True)
                bpy.ops.wm.quit_blender()
                return None
    except Exception:
        results.append({'test':'failure','traceback':traceback.format_exc()})
        RESULT.write_text(json.dumps(results,ensure_ascii=False,indent=2))
        traceback.print_exc()
        bpy.ops.wm.quit_blender()
        return None
    return 0.2

bpy.app.timers.register(tick, first_interval=2)
