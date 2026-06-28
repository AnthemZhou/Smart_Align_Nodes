import bpy


class SMART_ALIGN_NODES_PT_sidebar(bpy.types.Panel):
    bl_label = "Smart Align Nodes"
    bl_idname = "SMART_ALIGN_NODES_PT_sidebar"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Smart Align"

    def draw(self, context):
        layout = self.layout
        layout.operator("smart_align_nodes.debug_selected", icon="INFO")


classes = (
    SMART_ALIGN_NODES_PT_sidebar,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
