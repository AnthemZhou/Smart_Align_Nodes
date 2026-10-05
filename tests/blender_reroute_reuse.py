"""Background transaction tests for manual reroute identity and minimal writes."""
import bpy
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from smart_align_nodes.layout_route_adapter import *

t=bpy.data.node_groups.new('Reroute reuse regression','GeometryNodeTree')
a=t.nodes.new('ShaderNodeMath');a.name='a'
b=t.nodes.new('ShaderNodeMath');b.name='b'
r=t.nodes.new('NodeReroute');r.name='manual';r.label='Keep this label';r['user_data']='retained'
r.use_custom_color=True;r.color=(.2,.3,.4)
for n in t.nodes:n.select=True
r.location=(200,-300)
t.links.new(a.outputs[0],r.inputs[0]);t.links.new(r.outputs[0],b.inputs[0])
selected={'a','b'}
plan={'source':'a','target':'b','output':0,'input':0,'points':[(200,-37),(300,-37),(300,100),(600,100)]}
results=[]
def signature():
    return sorted(link_record(e) for e in t.links)
def points():
    return {n.name:tuple(n.location_absolute) for n in t.nodes}
assert routing_nodes(t)[1]=={'manual'}
ptr=r.as_pointer();before=signature();locations=points()
x=RouteTransaction(t,[plan],selected)
assert x.apply()==3 and r.as_pointer()==ptr
assert r.label=='Keep this label' and r['user_data']=='retained'
assert r.select and not r.get(ROUTE_TAG,False)
assert tuple(r.location)==(200,-37)
results.append({'test':'reuse_manual_identity_and_metadata','pass':True})
first=signature();first_points=points();names=generated_nodes(t)
y=RouteTransaction(t,[plan],selected)
assert y.apply()==0 and not y.operations
assert signature()==first and points()==first_points and generated_nodes(t)==names
results.append({'test':'unchanged_path_has_no_mutations','pass':True})
decorated=t.nodes[sorted(names)[0]];decorated.label='User annotated'
assert decorated.name not in generated_nodes(t)
decorated.label=''
results.append({'test':'annotated_auto_point_is_protected','pass':True})
short=dict(plan,points=[(200,-37),(500,-37)])
z=RouteTransaction(t,[short],selected);assert z.apply()==0
assert len(generated_nodes(t))==1 and r.as_pointer()==ptr
z.rollback();assert signature()==first and points()==first_points
assert r.label=='Keep this label' and r['user_data']=='retained' and r.as_pointer()==ptr
results.append({'test':'remove_surplus_auto_points_and_rollback','pass':True})
x.rollback();assert signature()==before and points()==locations and r.as_pointer()==ptr
results.append({'test':'rollback_first_route','pass':True})
b.select=False;assert not routing_nodes(t)[1]
b.select=True
r.outputs[0].links[0].is_muted=True;assert not routing_nodes(t)[1]
r.outputs[0].links[0].is_muted=False
c=t.nodes.new('ShaderNodeMath');c.name='external';c.select=False
t.links.new(r.outputs[0],c.inputs[0]);assert not routing_nodes(t)[1]
results.append({'test':'external_and_muted_and_branch_points_excluded','pass':True})
Path('/private/tmp/san_reroute_reuse_transactions.json').write_text(json.dumps(results,indent=2))
print('SAN_REUSE_TRANSACTIONS_PASS')
