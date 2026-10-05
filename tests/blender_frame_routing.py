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

fixture_name='frame_routing_layout'
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
    n.show_options=profile['type']=='GeometryNodeFieldOnDomain'
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
from smart_align_nodes.layout_route_adapter import generated_nodes, logical_links, socket_index
from smart_align_nodes import layout_operator
reuse_manual = bool(os.environ.get('SAN_REUSE_MANUAL_POINTS'))
if reuse_manual:
    source=tree.nodes['Reroute.197'];target=tree.nodes['Switch.007']
    out=source.outputs[0]
    for i in range(2):
        n=tree.nodes.new('NodeReroute');n.name=f'Manual Route {i+1}'
        n.parent=source.parent;n.select=True;n.label=f'Existing label {i+1}'
        n['user_marker']=i
        n.location=(700+i*150,-600)
        tree.links.new(out,n.inputs[0]);out=n.outputs[0]
    tree.links.new(out,target.inputs[1])
smart_align_nodes.register()
state={'step':-2};results=[]
output='/private/tmp/san_frame_routing_reuse' if reuse_manual else '/private/tmp/san_frame_routing'

def context():
    return bpy.context.temp_override(window=bpy.context.window,area=area,
                                    region=next(r for r in area.regions if r.type=='WINDOW'))
def positions():
    t=area.spaces.active.node_tree
    generated=generated_nodes(t)
    return {n.name:tuple(n.location_absolute) for n in t.nodes if n.name not in generated and n.type!='FRAME'}
def signature():
    t=area.spaces.active.node_tree
    return sorted((a.node.name,socket_index(a),b.node.name,socket_index(b),sort)
                  for a,b,sort,_ in logical_links(t,generated_nodes(t)))
def route_coordinates():
    t=area.spaces.active.node_tree
    return sorted(tuple(t.nodes[k].location_absolute) for k in generated_nodes(t))
def equal(a,b):
    assert a.keys()==b.keys()
    assert all(abs(a[k][i]-b[k][i])<.15 for k in a for i in (0,1)),(a,b)
def run(expected={'RUNNING_MODAL'}):
    assert bpy.ops.smart_align_nodes.auto_layout('INVOKE_DEFAULT')==expected
def fail_after_routes(self):
    state['original_apply'](self)
    raise RuntimeError('Injected routing failure')
def tick():
    try:
        with context():
            step=state['step']
            t=area.spaces.active.node_tree
            if step==-2:
                state['rollback_before']=positions();state['rollback_signature']=signature()
                run()
                assert generated_nodes(t), 'No route created before verification'
                state['original_capture']=layout_operator.capture_layout
                def fail_verification(*args,**kwargs):
                    raise RuntimeError('Injected verification failure after initial routing')
                layout_operator.capture_layout=fail_verification
                state['step']=-1;return .5
            if step==-1:
                layout_operator.capture_layout=state['original_capture']
                equal(positions(),state['rollback_before'])
                assert not generated_nodes(t) and signature()==state['rollback_signature']
                results.append({'test':'verification_failure_restores_initial_routes','pass':True})
                state['step']=0;return .2
            if step==0:
                bpy.ops.node.view_selected();state['before']=positions();state['signature']=signature()
                bpy.ops.ed.undo_push(message='Before routing regression')
                bpy.ops.screen.screenshot(filepath=output+'_before.png')
                run()
                # INVOKE has not returned to Blender's event loop: cards and
                # routes must already be applied together, before any redraw.
                assert generated_nodes(t), 'Routing was delayed until after the first redraw'
                state['first_apply_routes']=route_coordinates()
                state['step']=1;return 2
            if step==1:
                report=json.loads(bpy.data.texts['Smart Align Layout Debug'].as_string())
                assert report['metadata']['verified_after_redraw']
                assert report['metadata']['routing_applied_before_redraw']
                assert route_coordinates()==state['first_apply_routes']
                assert report['metrics']['generated_reroutes']>0,report
                if reuse_manual:
                    assert report['metrics']['generated_reroutes']==1,report
                    assert report['metrics']['reused_reroutes']==2,report
                    for i in range(2):
                        n=t.nodes[f'Manual Route {i+1}']
                        assert n.label==f'Existing label {i+1}' and n['user_marker']==i
                assert report['metrics']['node_overlaps']==0
                assert signature()==state['signature']
                state['after']=positions();state['routes']=route_coordinates()
                snap,links,_=capture_layout(t);boxes={n.key:n.box for n in snap}
                for key in ('Reroute.097','Reroute.197'):
                    edge=next(e for e in links if e.target==key)
                    assert abs(boxes[key].center_y-(boxes[edge.source].top-edge.source_offset))<.15
                for item in fixture['nodes']:
                    if not item['selected'] and item['kind']!='FRAME':
                        k=item['key'];assert max(abs(state['after'][k][i]-state['before'][k][i]) for i in (0,1))<.15
                results.append({'test':'junction_alignment_and_routing','pass':True,'report':report})
                bpy.ops.node.view_selected();state['step']=2;return .3
            if step==2:
                bpy.ops.screen.screenshot(filepath=output+'_after.png')
                run();state['step']=3;return 2
            if step==3:
                equal(positions(),state['after']);assert signature()==state['signature']
                rc=route_coordinates();assert len(rc)==len(state['routes'])
                assert all(abs(a[i]-b[i])<.15 for a,b in zip(rc,state['routes']) for i in (0,1))
                repeated=json.loads(bpy.data.texts['Smart Align Layout Debug'].as_string())
                assert repeated['metrics']['generated_reroutes']==0
                assert repeated['metadata']['location_writes']==0
                results.append({'test':'repeat_no_growth_or_drift','pass':True})
                bpy.ops.ed.undo();bpy.ops.ed.undo();state['step']=4;return .4
            if step==4:
                equal(positions(),state['before']);assert not generated_nodes(t);assert signature()==state['signature']
                results.append({'test':'undo_restores_nodes_and_links','pass':True})
                bpy.ops.ed.redo();state['step']=5;return .4
            if step==5:
                equal(positions(),state['after']);assert len(route_coordinates())==len(state['routes']);assert signature()==state['signature']
                results.append({'test':'redo_restores_routes','pass':True})
                bpy.ops.ed.undo();state['step']=6;return .4
            if step==6:
                t.nodes['Frame.020'].select=True
                bpy.ops.ed.undo_push(message='Select enclosing frame')
                run();state['step']=7;return 2
            if step==7:
                equal(positions(),state['after']);assert signature()==state['signature']
                assert len(route_coordinates())==len(state['routes'])
                results.append({'test':'frame_toggle_same_card_layout','pass':True})
                bpy.ops.screen.screenshot(filepath=output+'_frame_after.png')
                state['original_apply']=layout_operator.RouteTransaction.apply
                layout_operator.RouteTransaction.apply=fail_after_routes
                run({'CANCELLED'});state['step']=8;return 2
            if step==8:
                layout_operator.RouteTransaction.apply=state['original_apply']
                equal(positions(),state['after']);assert signature()==state['signature']
                assert len(route_coordinates())==len(state['routes'])
                results.append({'test':'injected_failure_restores_existing_routes','pass':True})
                state['route_names']=generated_nodes(t)
                for n in t.nodes:n.select=n.name in {'Named Attribute.001','Group Input.023'}
                run();state['step']=9;return 2
            if step==9:
                assert generated_nodes(t)==state['route_names']
                assert signature()==state['signature']
                results.append({'test':'unselected_generated_routes_preserved','pass':True})
                for n in t.nodes:n.select=any(item['key']==n.name and item['selected'] for item in fixture['nodes'])
                first=t.nodes[sorted(state['route_names'])[0]]
                first.outputs[0].links[0].is_muted=True
                run();state['step']=10;return 2
            if step==10:
                assert generated_nodes(t)==state['route_names']
                assert any(e.is_muted for e in t.links if e.from_node.name in state['route_names'])
                results.append({'test':'muted_generated_routes_preserved','pass':True})
                Path(output+'_results.json').write_text(json.dumps(results,indent=2))
                print('SAN_FRAME_ROUTING_PASS',flush=True);bpy.ops.wm.quit_blender();return None
    except Exception:
        results.append({'failure':traceback.format_exc()})
        Path(output+'_results.json').write_text(json.dumps(results,indent=2))
        traceback.print_exc();bpy.ops.wm.quit_blender();return None
    return .4
bpy.app.timers.register(tick,first_interval=2)
