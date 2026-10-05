"""GUI benchmark using drawn Math nodes; writes only temporary test results."""
from pathlib import Path
import json
import sys
import traceback
from time import perf_counter
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from smart_align_nodes.layout_adapter import capture_layout, apply_locations
from smart_align_nodes.layout import solve_layout, layout_diagnostics

bpy.context.preferences.view.show_splash=False
area=next(a for a in bpy.context.screen.areas if a.type=='VIEW_3D')
area.type='NODE_EDITOR'; area.ui_type='ShaderNodeTree'
mat=bpy.data.materials.new('SAN Benchmark'); mat.use_nodes=True
bpy.context.active_object.data.materials.clear(); bpy.context.active_object.data.materials.append(mat)
tree=mat.node_tree
cases=[(n,density) for n in (100,500,1000) for density in (1,3)]
state={'index':0,'phase':0}; results=[]
OUTPUT=Path('/private/tmp/smart_align_layout_benchmark.json')


def tick():
    try:
        if state['index']==len(cases):
            OUTPUT.write_text(json.dumps(results,indent=2)); print('SAN_BENCHMARK_PASS',flush=True)
            bpy.ops.wm.quit_blender(); return None
        n,density=cases[state['index']]
        if state['phase']==0:
            tree.nodes.clear()
            nodes=[]
            for i in range(n):
                node=tree.nodes.new('ShaderNodeMath'); node.operation='MULTIPLY_ADD'
                node.name=f'N{i:04d}'; node.location=((i%25)*200,-(i//25)*250)
                node.select=True; nodes.append(node)
            for i in range(n):
                for offset in range(1,density+1):
                    if i+offset<n: tree.links.new(nodes[i].outputs[0],nodes[i+offset].inputs[offset-1])
            area.tag_redraw(); state['phase']=1; return 1.0
        if state['phase']==1:
            snapshot,links,metadata=capture_layout(tree)
            plan=solve_layout(snapshot,links)
            started=perf_counter(); apply_locations(tree,plan.locations)
            state['row']={'nodes':n,'links':len(links),'density':density,
                          'snapshot_ms':metadata['snapshot_ms'],'solve_ms':plan.metrics['solve_ms'],
                          'write_ms':(perf_counter()-started)*1000,
                          'width':plan.metrics['width'],'height':plan.metrics['height'],
                          'fixed_conflicts':plan.metrics['fixed_conflicts']}
            started=perf_counter()
            state['row'].update(layout_diagnostics(snapshot,links,plan.boxes))
            state['row']['diagnostic_ms']=(perf_counter()-started)*1000
            state['locations']=plan.locations
            area.tag_redraw(); state['phase']=2; return .6
        snapshot,links,metadata=capture_layout(tree)
        repeated=solve_layout(snapshot,links)
        delta=max(abs(repeated.locations[node.key][i]-node.location[i]) for node in snapshot for i in (0,1))
        assert delta<.1,delta
        state['row']['repeat_max_delta']=delta
        results.append(state['row']); print('SAN_BENCHMARK',json.dumps(state['row']),flush=True)
        state['index']+=1; state['phase']=0; return .1
    except Exception:
        results.append({'failure':traceback.format_exc()}); OUTPUT.write_text(json.dumps(results,indent=2))
        traceback.print_exc(); bpy.ops.wm.quit_blender(); return None

bpy.app.timers.register(tick,first_interval=1.5)
