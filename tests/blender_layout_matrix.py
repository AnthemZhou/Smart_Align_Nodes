"""Isolated GUI checks. Run with --factory-startup --enable-event-simulate --python."""
import json
from pathlib import Path
import sys
import traceback
import bpy

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import smart_align_nodes
from smart_align_nodes import layout_operator
from smart_align_nodes.layout_adapter import capture_layout
from smart_align_nodes.layout import overlaps

bpy.context.preferences.view.show_splash=False
area=next(a for a in bpy.context.screen.areas if a.type=='VIEW_3D')
area.type='NODE_EDITOR'; area.ui_type='ShaderNodeTree'
mat=bpy.data.materials.new('SAN Matrix'); mat.use_nodes=True
bpy.context.active_object.data.materials.clear(); bpy.context.active_object.data.materials.append(mat)
tree=mat.node_tree
smart_align_nodes.register()
RESULT=Path('/private/tmp/smart_align_layout_matrix_results.json')
cases=['frame_only','children_only','partial_frame','nested','manual','collapsed','offscreen',
       'ui_scale','cancel','failure_rollback','shortcut','multi_input']
if __import__('os').environ.get('SAN_CASES'):
    cases=__import__('os').environ['SAN_CASES'].split(',')
state={'index':int(__import__('os').environ.get('SAN_START_CASE', '0')),'phase':0}
results=[]
original_solver=layout_operator.solve_layout
original_capture=layout_operator.capture_layout


def override():
    return bpy.context.temp_override(window=bpy.context.window,area=area,
                                    region=next(r for r in area.regions if r.type=='WINDOW'))


def positions():
    return {n.name:tuple(n.location_absolute) for n in tree.nodes}


def signature():
    return {'nodes':[(n.name,n.bl_idname,n.parent.name if n.parent else None,n.select,n.hide,
                      getattr(n,'shrink',None)) for n in tree.nodes],
            'links':[(l.from_node.name,l.from_socket.identifier,l.to_node.name,l.to_socket.identifier,
                      l.multi_input_sort_id) for l in tree.links]}


def close(a,b):
    return all(abs(a[k][i]-v[i])<.15 for k,v in b.items() for i in (0,1))


def setup(case):
    global tree
    tree.nodes.clear()
    if case=='multi_input':
        tree=bpy.data.node_groups.new('SAN Geometry','GeometryNodeTree')
        area.ui_type='GeometryNodeTree'
        modifier=bpy.context.active_object.modifiers.new('SAN Test','NODES'); modifier.node_group=tree
        a=tree.nodes.new('GeometryNodeMeshCube'); a.name='A'; a.location=(0,0)
        b=tree.nodes.new('GeometryNodeMeshUVSphere'); b.name='B'; b.location=(20,-500)
        c=tree.nodes.new('GeometryNodeJoinGeometry'); c.name='C'; c.location=(500,0)
        tree.links.new(a.outputs[0],c.inputs[0]); tree.links.new(b.outputs[0],c.inputs[0])
        return
    f=tree.nodes.new('NodeFrame'); f.name='Frame'
    a=tree.nodes.new('ShaderNodeValue'); a.name='A'; a.parent=f; a.location=(30,-80)
    b=tree.nodes.new('ShaderNodeMath'); b.name='B'; b.parent=f; b.location=(40,-400)
    c=tree.nodes.new('ShaderNodeMath'); c.name='C'; c.location=(500,-100)
    sibling=tree.nodes.new('ShaderNodeValue'); sibling.name='Sibling'; sibling.parent=f; sibling.location=(30,-650)
    sibling.select=False
    fixed=tree.nodes.new('ShaderNodeValue'); fixed.name='Fixed'; fixed.location=(1300,0); fixed.select=False
    tree.links.new(a.outputs[0],b.inputs[0]); tree.links.new(b.outputs[0],c.inputs[0])
    for n in (a,b,c,f): n.select=True
    if case=='frame_only': a.select=b.select=False
    if case=='children_only': f.select=c.select=False
    if case=='nested':
        inner=tree.nodes.new('NodeFrame'); inner.name='Inner'; inner.parent=f; inner.location=(20,-50)
        a.parent=inner; b.parent=inner; sibling.parent=inner
        inner.select=True
    if case=='manual': f.shrink=False; f.width=900; f.height=900
    if case=='collapsed': a.hide=True; b.hide=True; b.inputs[1].hide=True
    if case=='offscreen': c.location=(50000,-10000)
    if case=='ui_scale': bpy.context.preferences.view.ui_scale=1.25


def tick():
    try:
        with override():
            if state['index']>=len(cases):
                smart_align_nodes.unregister()
                RESULT.write_text(json.dumps(results,indent=2))
                print('SAN_MATRIX_PASS',flush=True); bpy.ops.wm.quit_blender(); return None
            case=cases[state['index']]
            phase=state['phase']
            if phase==0:
                setup(case); state['phase']=1; area.tag_redraw(); return .6
            if phase==1:
                snap,links,meta=capture_layout(tree)
                state['before']=positions(); state['signature']=signature()
                state['manual_size']=(tree.nodes['Frame'].width,tree.nodes['Frame'].height) if case=='manual' else None
                old=bpy.data.texts.get('Smart Align Layout Debug')
                if old: bpy.data.texts.remove(old)
                if case=='shortcut':
                    bpy.context.window.event_simulate(type='O',value='PRESS',oskey=True,x=200,y=300)
                else:
                    result=bpy.ops.smart_align_nodes.auto_layout('INVOKE_DEFAULT')
                    assert result=={'RUNNING_MODAL'}, (case,result)
                if case=='cancel':
                    bpy.context.window.event_simulate(type='ESC',value='PRESS',x=200,y=200)
                if case=='failure_rollback':
                    def fail(*args,**kwargs): raise RuntimeError('Injected redraw failure')
                    layout_operator.capture_layout=fail
                state['phase']=2; return .7
            if phase==2:
                layout_operator.solve_layout=original_solver
                layout_operator.capture_layout=original_capture
                assert signature()==state['signature'], (case,'topology/selection/parent changed')
                if case in ('cancel','failure_rollback'):
                    assert close(positions(),state['before']), (case,'rollback failed',positions(),state['before'])
                    results.append({'test':case,'pass':True}); state['index']+=1; state['phase']=0; return .2
                report=bpy.data.texts.get('Smart Align Layout Debug')
                assert report, (case,'did not finish')
                report=json.loads(report.as_string())
                assert report['metadata']['verified_after_redraw']
                if 'Fixed' in tree.nodes: assert close({'Fixed':positions()['Fixed']},{'Fixed':state['before']['Fixed']})
                if case=='children_only':
                    assert close({'Sibling':positions()['Sibling'],'C':positions()['C']},
                                 {'Sibling':state['before']['Sibling'],'C':state['before']['C']})
                if case=='frame_only':
                    assert {'A','B','Sibling'} <= set(report['metadata']['layout_selection'])
                    assert positions()['B'][0] > positions()['A'][0] + tree.nodes['A'].width
                    assert not tree.nodes['A'].select and not tree.nodes['B'].select
                if case=='manual':
                    assert abs(tree.nodes['Frame'].width-state['manual_size'][0])<.15
                    assert abs(tree.nodes['Frame'].height-state['manual_size'][1])<.15
                if case=='partial_frame':
                    state['normal_scale_positions']=positions()
                if case=='ui_scale' and 'normal_scale_positions' in state:
                    # UI scaling changes drawn control heights even after DPI
                    # normalization (Math: 149 -> 144.8 here). Identical Y is
                    # incompatible with aligned ports on these actual bounds.
                    # Columns stay fixed; verify the main wires on freshly
                    # drawn geometry, plus the repeat check below.
                    assert all(abs(positions()[k][0]-v[0])<1.0
                               for k,v in state['normal_scale_positions'].items()), 'UI scale changed columns'
                    drawn,drawn_links,_=capture_layout(tree)
                    boxes={n.key:n.box for n in drawn}
                    for e in drawn_links:
                        assert abs((boxes[e.source].top-e.source_offset)-
                                   (boxes[e.target].top-e.target_offset))<.15, ('UI scale broke socket alignment',e)
                state['after']=positions(); state['report']=report
                bpy.ops.smart_align_nodes.auto_layout('INVOKE_DEFAULT')
                state['phase']=3; return .7
            if phase==3:
                assert close(positions(),state['after']), (case,'repeat drift',positions(),state['after'])
                assert signature()==state['signature']
                results.append({'test':case,'pass':True,'metrics':state['report']['metrics'],
                                'redraw_passes':state['report']['metadata']['redraw_passes'],
                                'warnings':state['report']['warnings']})
                print('MATRIX_CASE_PASS',case,flush=True)
                state['index']+=1; state['phase']=0; return .2
    except Exception:
        layout_operator.solve_layout=original_solver
        layout_operator.capture_layout=original_capture
        results.append({'test':cases[state['index']],'failure':traceback.format_exc()})
        RESULT.write_text(json.dumps(results,indent=2)); traceback.print_exc()
        bpy.ops.wm.quit_blender(); return None
    return .2

bpy.app.timers.register(tick,first_interval=1.5)
