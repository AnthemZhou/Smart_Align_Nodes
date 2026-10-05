"""Background checks for registration and restoration of existing move hooks."""
from pathlib import Path
import sys
import bpy
from bl_operators import node as builtin_node
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import smart_align_nodes as addon


class NODE_OT_console_test(bpy.types.Operator):
    bl_idname='node.node_console'
    bl_label='Temporary Node Console bridge test'
    def _start_native_node_transform(self, context):
        return False
    def execute(self,context):
        return {'FINISHED'}


bpy.utils.register_class(NODE_OT_console_test)
original=builtin_node.NodeAddOperator.invoke
console_original=NODE_OT_console_test._start_native_node_transform
for iteration in range(2):
    addon.register()
    from smart_align_nodes import operators
    assert bpy.ops.smart_align_nodes.auto_layout.get_rna_type()
    assert builtin_node.NodeAddOperator.invoke != original
    assert NODE_OT_console_test._start_native_node_transform != console_original
    bindings=[(item.idname,item.type,item.oskey,item.ctrl,item.shift) for _,item in operators.addon_keymaps]
    assert len(bindings)==4
    assert ('smart_align_nodes.auto_layout','O',1,0,0) in bindings
    assert ('smart_align_nodes.move_with_snap','G',0,0,0) in bindings
    assert ('smart_align_nodes.duplicate_move','D',0,0,1) in bindings
    assert not bpy.ops.smart_align_nodes.auto_layout.poll(), 'Must reject non-node editor'
    addon.unregister()
    assert builtin_node.NodeAddOperator.invoke == original
    assert NODE_OT_console_test._start_native_node_transform == console_original
    assert not operators.addon_keymaps
    assert not bpy.app.timers.is_registered(operators._watch_node_console)
bpy.utils.unregister_class(NODE_OT_console_test)
print('SAN_REGISTRATION_PASS: two cycles, keymaps, add hook, Node Console stub, timer cleanup')
