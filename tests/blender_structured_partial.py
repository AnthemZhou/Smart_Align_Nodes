"""Recreate the reported branch selection in an isolated factory-startup GUI."""
import json
import os
import sys
import traceback
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import smart_align_nodes
from smart_align_nodes.layout_adapter import capture_layout, apply_locations

fixture_name=os.environ.get('SAN_LAYOUT_FIXTURE','partial_branch_layout')
fixture=json.loads((Path(__file__).parent/'fixtures'/f'{fixture_name}.json').read_text())
output=f'/private/tmp/san_internal_{fixture_name}'
bpy.context.preferences.view.show_splash=False
area=next(a for a in bpy.context.screen.areas if a.type=='VIEW_3D')
area.type='NODE_EDITOR';area.ui_type='GeometryNodeTree'
tree=bpy.data.node_groups.new('Structured partial regression','GeometryNodeTree')
area.spaces.active.show_region_ui=False
area.spaces.active.pin=True
area.spaces.active.node_tree=tree
# Rebuild the interface for retained external Group Input endpoints. Menu
# sockets are never used by this fixture; keep a type-compatible placeholder
# if this Blender build does not expose them through interface.new_socket.
socket_types={'GEOMETRY':'NodeSocketGeometry','VALUE':'NodeSocketFloat','INT':'NodeSocketInt',
              'BOOLEAN':'NodeSocketBool','MENU':'NodeSocketMenu','OBJECT':'NodeSocketObject',
              'STRING':'NodeSocketString','VECTOR':'NodeSocketVector',
              'MATRIX':'NodeSocketMatrix','RGBA':'NodeSocketColor'}
for profile in fixture['socket_profiles'].values():
    if profile['type']=='NodeGroupInput':
        for socket in profile['outputs']:
            if socket['identifier']=='__extend__': continue
            try:
                tree.interface.new_socket(name=socket['identifier'],in_out='INPUT',socket_type=socket_types[socket['type']])
            except TypeError:
                tree.interface.new_socket(name=socket['identifier'],in_out='INPUT',socket_type='NodeSocketFloat')
        break
for item in fixture['nodes']:
    profile=fixture['socket_profiles'][item['key']]
    n=tree.nodes.new(profile['type']);n.name=item['key']
    if profile['type']=='GeometryNodeSwitch':
        n.input_type={'VALUE':'FLOAT'}.get(profile['outputs'][0]['type'],profile['outputs'][0]['type'])
    if profile['type']=='NodeReroute':
        n.socket_idname=socket_types[profile['outputs'][0]['type']]
    for k,v in profile['properties'].items():
        setattr(n,k,v)
    n.width=item['box'][1]-item['box'][0]
    n.hide=profile['hide']
    n.show_options=False
    for direction in ('inputs','outputs'):
        for s,p in zip(getattr(n,direction),profile[direction]): s.hide=p['hide']
for item in fixture['nodes']:
    n=tree.nodes[item['key']]
    if item.get('parent'): n.parent=tree.nodes[item['parent']]
    n.select=item['selected']
apply_locations(tree,{item['key']:tuple(item['location']) for item in fixture['nodes']})
for e in fixture['links']:
    tree.links.new(tree.nodes[e['source']].outputs[e['output']],tree.nodes[e['target']].inputs[e['input']])
# Trimming the original tree leaves some external inputs dangling, especially
# reroutes. Supply their original types so Blender does not draw default-value
# controls which were absent in the captured graph.
connected={(e['target'],e['input']) for e in fixture['links']}
missing=[(key,i,p['type']) for key,profile in fixture['socket_profiles'].items()
         for i,p in enumerate(profile['inputs'])
         if p['is_linked'] and (key,i) not in connected]
if missing:
    identifiers={}
    for kind in sorted({kind for _,_,kind in missing}):
        identifiers[kind]=tree.interface.new_socket(name='External '+kind,in_out='INPUT',
                                                    socket_type=socket_types[kind]).identifier
    source=tree.nodes.new('NodeGroupInput');source.name='Fixture External Inputs'
    source.location=(-4000,3000);source.hide=True;source.select=False
    for key,index,kind in missing:
        socket=next(s for s in source.outputs if s.identifier==identifiers[kind])
        tree.links.new(socket,tree.nodes[key].inputs[index])
smart_align_nodes.register()
from smart_align_nodes.layout_route_adapter import generated_nodes, logical_links, socket_index
state={'step':0}
result=[]

def context():
    return bpy.context.temp_override(window=bpy.context.window,area=area,
                                    region=next(r for r in area.regions if r.type=='WINDOW'))
def positions():
    t=area.spaces.active.node_tree
    generated=generated_nodes(t)
    return {n.name:tuple(n.location_absolute) for n in t.nodes if n.name not in generated}
def routing_state():
    t=area.spaces.active.node_tree
    generated=generated_nodes(t)
    points=sorted(tuple(round(v,2) for v in t.nodes[k].location_absolute) for k in generated)
    links=sorted((a.node.name,socket_index(a),b.node.name,socket_index(b),order)
                 for a,b,order,_ in logical_links(t,generated))
    return points,links
def equal(expected):
    actual=positions()
    assert actual.keys()==expected.keys()
    assert all(abs(actual[k][i]-v[i])<.15 for k,v in expected.items() for i in (0,1))
def tick():
    try:
        with context():
            step=state['step']
            if step==0:
                bpy.ops.node.view_selected()
                state['step']=1
                return .4
            if step==1:
                bpy.ops.screen.screenshot(filepath=output+'_before.png')
                state['before']=positions()
                state['routing_before']=routing_state()
                bpy.ops.ed.undo_push(message='Before structured layout')
                assert bpy.ops.smart_align_nodes.auto_layout('INVOKE_DEFAULT')=={'RUNNING_MODAL'}
                state['step']=2
                return 2.0
            if step==2:
                report=json.loads(bpy.data.texts['Smart Align Layout Debug'].as_string())
                assert report['metadata']['verified_after_redraw']
                assert report['metrics']['moved']>0,report
                assert report['metrics']['node_overlaps']==0,report
                assert report['metrics']['wire_scope']=='selection_internal'
                if fixture_name=='partial_eight_layout':
                    assert report['metrics']['moved']>0,report
                    assert report['metrics']['internal_links_checked']==9,report
                else:
                    for a,b in (('Switch.022','Switch.025'),('Separate XYZ.002','Separate XYZ.003'),('Math.040','Math.041')):
                        assert abs(positions()[a][0]-positions()[b][0])<.15,(a,b)
                    for a,b in (('Position.004','Transform Point'),('Transform Point','Separate XYZ.002'),
                                ('Separate Transform','Combine Transform')):
                        assert report['alignment_decisions'][a]['vertical']=='top',(a,b,report)
                        assert abs(positions()[a][1]-positions()[b][1])<.15,(a,b)
                    assert report['alignment_decisions']['Math.051']['vertical']=='socket'
                state['after']=positions()
                state['routing_after']=routing_state()
                assert state['routing_after'][1]==state['routing_before'][1]
                for n in fixture['nodes']:
                    if not n['selected']:
                        assert all(abs(state['after'][n['key']][i]-state['before'][n['key']][i])<.15
                                   for i in (0,1)), n['key']
                result.append({'test':'hybrid_alignment_and_fixed_nodes','pass':True,'report':report})
                bpy.ops.node.view_selected()
                state['step']=3
                return .4
            if step==3:
                bpy.ops.screen.screenshot(filepath=output+'_after.png')
                bpy.ops.smart_align_nodes.auto_layout('INVOKE_DEFAULT')
                state['step']=4
                return 2.0
            if step==4:
                equal(state['after'])
                assert routing_state()==state['routing_after']
                result.append({'test':'repeat_stability','pass':True})
                # The second invocation is a separate undo entry.
                bpy.ops.ed.undo();bpy.ops.ed.undo()
                state['step']=5
                return .5
            if step==5:
                equal(state['before'])
                assert routing_state()==state['routing_before']
                result.append({'test':'undo_restores_original','pass':True})
                bpy.ops.ed.redo()
                state['step']=6
                return .5
            if step==6:
                equal(state['after'])
                assert routing_state()==state['routing_after']
                result.append({'test':'redo_restores_alignment','pass':True})
                Path(output+'_results.json').write_text(json.dumps(result,indent=2))
                print('SAN_INTERNAL_PASS',flush=True)
                bpy.ops.wm.quit_blender()
                return None
    except Exception:
        result.append({'failure':traceback.format_exc()})
        Path(output+'_results.json').write_text(json.dumps(result,indent=2))
        traceback.print_exc();bpy.ops.wm.quit_blender()
        return None
    return .5
bpy.app.timers.register(tick,first_interval=2)
